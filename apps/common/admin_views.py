"""
API views для административных функций (логи, аудит, бэкапы)
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.db import connection
from django.conf import settings as django_settings
from django.utils import timezone
from datetime import datetime, timedelta
import os
import subprocess
import sys
import shutil
import glob

from .models import Log, AuditLog, Backup, BackupSchedule
from .serializers import LogSerializer, AuditLogSerializer, BackupSerializer, CreateBackupSerializer, BackupScheduleSerializer
from .permissions import IsAdmin
from .data_integrity import DataIntegrityChecker
from drf_spectacular.utils import extend_schema


def _get_pg_bin_dir():
    """
    Возвращает каталог bin PostgreSQL (содержит pg_dump, pg_restore).
    На Windows эти утилиты часто не в PATH.
    """
    # Явный путь к pg_dump из настроек — используем его каталог для pg_restore
    custom = getattr(django_settings, 'PG_DUMP_PATH', None)
    if custom and os.path.isfile(custom):
        return os.path.dirname(custom)
    
    if shutil.which('pg_dump'):
        return os.path.dirname(shutil.which('pg_dump'))
    
    if sys.platform == 'win32':
        program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
        for base in (program_files, program_files_x86):
            pattern = os.path.join(base, 'PostgreSQL', '*', 'bin')
            for dirpath in glob.glob(pattern):
                if os.path.isfile(os.path.join(dirpath, 'pg_dump.exe')):
                    return dirpath
        pgpath = os.environ.get('PGPATH', '')
        if pgpath:
            bindir = os.path.join(pgpath, 'bin')
            if os.path.isfile(os.path.join(bindir, 'pg_dump.exe')):
                return bindir
    
    return None


def _get_pg_dump_path():
    """Путь к pg_dump."""
    bindir = _get_pg_bin_dir()
    if bindir:
        exe = 'pg_dump.exe' if sys.platform == 'win32' else 'pg_dump'
        return os.path.join(bindir, exe)
    return 'pg_dump'


def _get_pg_restore_path():
    """Путь к pg_restore."""
    bindir = _get_pg_bin_dir()
    if bindir:
        exe = 'pg_restore.exe' if sys.platform == 'win32' else 'pg_restore'
        return os.path.join(bindir, exe)
    return 'pg_restore'


def _get_backup_dir():
    """Каталог для сохранения бекапов (кроссплатформенно)."""
    default = os.path.join(django_settings.BASE_DIR, 'backups')
    return getattr(django_settings, 'BACKUP_DIR', default)


class LogListAPIView(generics.ListAPIView):
    """Список операционных логов (только для администраторов)"""
    queryset = Log.objects.select_related('user').all()
    serializer_class = LogSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['level', 'user']
    ordering_fields = ['ts', 'level']
    ordering = ['-ts']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтрация по дате
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            try:
                date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                queryset = queryset.filter(ts__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                queryset = queryset.filter(ts__lte=date_to)
            except ValueError:
                pass
        
        return queryset


class AuditLogListAPIView(generics.ListAPIView):
    """Список записей аудита (только для администраторов)"""
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['action', 'table_name', 'user']
    ordering_fields = ['ts', 'action', 'table_name']
    ordering = ['-ts']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтрация по дате
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            try:
                date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                queryset = queryset.filter(ts__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                queryset = queryset.filter(ts__lte=date_to)
            except ValueError:
                pass
        
        return queryset


class BackupListAPIView(generics.ListAPIView):
    """Список резервных копий (только для администраторов)"""
    queryset = Backup.objects.select_related('created_by').all()
    serializer_class = BackupSerializer
    permission_classes = [IsAdmin]
    ordering = ['-ts']


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_backup_view(request):
    """
    Создание резервной копии БД
    
    POST /api/v1/admin/backups/create/
    """
    serializer = CreateBackupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    description = serializer.validated_data.get('description', '')
    
    try:
        db_settings = django_settings.DATABASES['default']
        
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings.get('PASSWORD', '')
        db_host = db_settings.get('HOST', 'localhost')
        db_port = db_settings.get('PORT', '5432')
        
        pg_dump_path = _get_pg_dump_path()
        if not os.path.isfile(pg_dump_path) and pg_dump_path == 'pg_dump':
            return Response(
                {'error': 'pg_dump не найден. Установите PostgreSQL и добавьте папку bin в PATH, '
                          'либо укажите PG_DUMP_PATH в настройках (например, в settings.py).'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Каталог для бекапов (на Windows по умолчанию: проект/backups)
        backup_dir = _get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'shop_backup_{timestamp}.dump'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = db_password
        
        cmd = [
            pg_dump_path,
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '-F', 'c',
            '-f', backup_path
        ]
        
        # Выполняем pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 минут таймаут
        )
        
        if result.returncode != 0:
            return Response(
                {'error': f'Ошибка создания резервной копии: {result.stderr}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Создаём запись в БД из Python с правильным путём (функция create_backup в БД возвращает путь, а не id)
        backup = Backup.objects.create(
            file_path=backup_path,
            created_by_id=request.user.id,
            status='Completed',
            description=(description or '').strip() or None,
        )
        
        return Response({
            'id': backup.id,
            'file_path': backup_path,
            'status': 'Completed',
            'message': 'Резервная копия успешно создана'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка создания резервной копии: {e}')
        return Response(
            {'error': f'Ошибка создания резервной копии: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdmin])
def download_backup_view(request, backup_id):
    """
    Скачивание резервной копии
    
    GET /api/v1/admin/backups/{id}/download/
    """
    try:
        backup = Backup.objects.get(id=backup_id)
        
        if not backup.file_path or not (backup.file_path or '').strip():
            return Response(
                {'error': 'У этой резервной копии не указан путь к файлу.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Путь из БД мог быть записан по старым настройкам (/var/backups или др.)
        # Пробуем текущий каталог бекапов с тем же именем файла
        file_path_to_use = backup.file_path
        if not os.path.exists(file_path_to_use):
            fallback_dir = _get_backup_dir()
            fallback_path = os.path.join(fallback_dir, os.path.basename(backup.file_path))
            if os.path.exists(fallback_path):
                file_path_to_use = fallback_path
            else:
                return Response(
                    {'error': f'Файл резервной копии не найден: {backup.file_path}. '
                              'Раньше использовался каталог /var/backups — создайте новый бекап, он сохранится в папку backups проекта.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        from django.http import FileResponse
        import mimetypes
        
        mime_type, _ = mimetypes.guess_type(file_path_to_use)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        filename = os.path.basename(file_path_to_use)
        
        response = FileResponse(
            open(file_path_to_use, 'rb'),
            content_type=mime_type
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Backup.DoesNotExist:
        return Response(
            {'error': 'Резервная копия не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка скачивания резервной копии: {e}')
        return Response(
            {'error': f'Ошибка скачивания резервной копии: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdmin])
def restore_backup_view(request, backup_id):
    """
    Восстановление из резервной копии
    
    POST /api/v1/admin/backups/{id}/restore/
    """
    try:
        backup = Backup.objects.get(id=backup_id)
        
        if not os.path.exists(backup.file_path):
            return Response(
                {'error': 'Файл резервной копии не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        db_settings = django_settings.DATABASES['default']
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings.get('PASSWORD', '')
        db_host = db_settings.get('HOST', 'localhost')
        db_port = db_settings.get('PORT', '5432')
        
        pg_restore_path = _get_pg_restore_path()
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = db_password
        
        cmd = [
            pg_restore_path,
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '--clean',
            '--if-exists',
            backup.file_path
        ]
        
        # Выполняем pg_restore
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 минут таймаут
        )
        
        if result.returncode != 0:
            return Response(
                {'error': f'Ошибка восстановления: {result.stderr}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'База данных успешно восстановлена из резервной копии'
        }, status=status.HTTP_200_OK)
        
    except Backup.DoesNotExist:
        return Response(
            {'error': 'Резервная копия не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка восстановления: {e}')
        return Response(
            {'error': f'Ошибка восстановления: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT'])
@permission_classes([IsAdmin])
def backup_schedule_view(request):
    """
    Получение и обновление расписания автоматических бекапов
    
    GET /api/v1/admin/backups/schedule/
    PUT /api/v1/admin/backups/schedule/
    """
    # Получаем или создаём единственную запись расписания
    schedule, created = BackupSchedule.objects.get_or_create(pk=1, defaults={
        'is_enabled': False,
        'frequency': 'daily',
        'time': '02:00',
        'keep_days': 30,
    })
    
    if request.method == 'GET':
        serializer = BackupScheduleSerializer(schedule)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = BackupScheduleSerializer(schedule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Проверка целостности данных",
    description="Проверка целостности данных в базе данных (заказы, корзина, транзакции)",
    tags=['Admin'],
)
@api_view(['GET'])
@permission_classes([IsAdmin])
def check_data_integrity_view(request):
    """
    Проверка целостности данных
    
    GET /api/v1/admin/integrity/check/
    """
    try:
        result = DataIntegrityChecker.run_all_checks()
        
        # Логируем проверку
        Log.objects.create(
            level='INFO',
            message=f'Data integrity check completed: {result["total_issues"]} issues found',
            user_id=request.user.id,
            meta={
                'action': 'data_integrity_check',
                'total_issues': result['total_issues'],
                'status': result['status']
            }
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка проверки целостности данных: {e}')
        
        Log.objects.create(
            level='ERROR',
            message=f'Data integrity check failed: {str(e)}',
            user_id=request.user.id if request.user.is_authenticated else None,
            meta={'action': 'data_integrity_check_failed', 'error': str(e)}
        )
        
        return Response(
            {'error': f'Ошибка проверки целостности данных: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

