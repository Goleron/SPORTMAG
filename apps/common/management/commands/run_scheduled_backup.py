"""
Команда для запуска автоматических резервных копий по расписанию.
"""
import os
import subprocess
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.models import Backup, BackupSchedule


class Command(BaseCommand):
    help = 'Проверяет расписание и при необходимости создаёт автоматический бэкап БД'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Создать бэкап принудительно, игнорируя расписание',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        schedule, _ = BackupSchedule.objects.get_or_create(
            pk=1,
            defaults={
                'is_enabled': False,
                'frequency': 'daily',
                'time': '02:00',
                'keep_days': 30,
            },
        )
        now = timezone.localtime()

        if not force and not schedule.is_enabled:
            self.stdout.write(self.style.WARNING('Автоматические бэкапы отключены'))
            return

        if not force and not self._should_run(schedule, now):
            self.stdout.write(self.style.NOTICE('Время бэкапа ещё не наступило'))
            return

        backup_path, error_message = self._create_backup_file(now)
        if error_message:
            Backup.objects.create(
                file_path=backup_path,
                status='Failed',
                description=f'Автоматический бэкап: {error_message}',
                created_by=None,
            )
            self.stderr.write(self.style.ERROR(f'Ошибка создания бэкапа: {error_message}'))
            return

        Backup.objects.create(
            file_path=backup_path,
            status='Completed',
            description='Автоматическое резервное копирование',
            created_by=None,
        )

        schedule.last_run = now
        schedule.save(update_fields=['last_run', 'updated_at'])
        self._cleanup_old_backups(schedule.keep_days)

        self.stdout.write(self.style.SUCCESS(f'Бэкап успешно создан: {backup_path}'))

    def _should_run(self, schedule, now):
        """Определить, нужно ли запускать бэкап в текущий момент."""
        if now.time().replace(second=0, microsecond=0) < schedule.time:
            return False

        if not schedule.last_run:
            return True

        last_run = timezone.localtime(schedule.last_run)
        if schedule.frequency == 'daily':
            return last_run.date() < now.date()

        if schedule.frequency == 'weekly':
            start_of_week = now.date() - timedelta(days=now.weekday())
            return last_run.date() < start_of_week

        if schedule.frequency == 'monthly':
            start_of_month = now.date().replace(day=1)
            return last_run.date() < start_of_month

        return False

    def _create_backup_file(self, now):
        """Создать файл резервной копии через pg_dump."""
        db_settings = settings.DATABASES.get('default', {})
        if db_settings.get('ENGINE') != 'django.db.backends.postgresql':
            return 'unsupported_engine', 'Резервное копирование поддерживается только для PostgreSQL'

        backup_dir = Path(getattr(settings, 'BACKUP_DIR', Path(settings.BASE_DIR) / 'backups'))
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_filename = f"shop_backup_{now.strftime('%Y%m%d_%H%M%S')}.dump"
        backup_path = backup_dir / backup_filename

        env = os.environ.copy()
        db_password = db_settings.get('PASSWORD', '')
        if db_password:
            env['PGPASSWORD'] = db_password

        cmd = [
            'pg_dump',
            '-h', db_settings.get('HOST', 'localhost'),
            '-p', str(db_settings.get('PORT', '5432')),
            '-U', db_settings.get('USER', 'postgres'),
            '-d', db_settings.get('NAME'),
            '-F', 'c',
            '-f', str(backup_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return str(backup_path), 'Истек таймаут выполнения pg_dump'
        except Exception as exc:
            return str(backup_path), str(exc)

        if result.returncode != 0:
            error_message = (result.stderr or 'Неизвестная ошибка pg_dump').strip()
            return str(backup_path), error_message

        return str(backup_path), None

    def _cleanup_old_backups(self, keep_days):
        """Удалить старые файлы и записи бэкапов старше keep_days."""
        cutoff = timezone.now() - timedelta(days=max(1, int(keep_days)))
        old_backups = Backup.objects.filter(ts__lt=cutoff)
        for backup in old_backups:
            try:
                if backup.file_path and os.path.exists(backup.file_path):
                    os.remove(backup.file_path)
            except OSError:
                # Ошибка удаления файла не должна прерывать cleanup записей.
                pass
        old_backups.delete()

