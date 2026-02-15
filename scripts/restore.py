#!/usr/bin/env python
"""
Скрипт для восстановления базы данных из резервной копии
"""
import os
import sys
import django
import subprocess

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.db import connection
from apps.common.models import Backup


def restore_backup(backup_id):
    """
    Восстановить базу данных из резервной копии
    
    Args:
        backup_id: ID резервной копии в БД
    
    Returns:
        bool: True если восстановление успешно
    """
    try:
        backup = Backup.objects.get(id=backup_id)
        
        if not os.path.exists(backup.file_path):
            print(f'Ошибка: Файл резервной копии не найден: {backup.file_path}')
            return False
        
        # Получаем настройки БД
        db_settings = settings.DATABASES['default']
        
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings.get('PASSWORD', '')
        db_host = db_settings.get('HOST', 'localhost')
        db_port = db_settings.get('PORT', '5432')
        
        # Создаем команду pg_restore
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = db_password
        
        cmd = [
            'pg_restore',
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '--clean',  # Очистить перед восстановлением
            '--if-exists',
            backup.file_path
        ]
        
        print(f'Восстановление из резервной копии: {backup.file_path}')
        print('⚠️  ВНИМАНИЕ: Все текущие данные будут заменены!')
        
        # Запрашиваем подтверждение
        confirm = input('Продолжить восстановление? (yes/no): ')
        if confirm.lower() != 'yes':
            print('Восстановление отменено')
            return False
        
        # Выполняем pg_restore
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 минут таймаут
        )
        
        if result.returncode != 0:
            print(f'Ошибка восстановления: {result.stderr}')
            return False
        
        print('База данных успешно восстановлена из резервной копии')
        return True
        
    except Backup.DoesNotExist:
        print(f'Ошибка: Резервная копия с ID={backup_id} не найдена')
        return False
    except subprocess.TimeoutExpired:
        print('Ошибка: Превышено время ожидания при восстановлении')
        return False
    except Exception as e:
        print(f'Ошибка восстановления: {e}')
        return False


def list_backups():
    """Вывести список доступных резервных копий"""
    backups = Backup.objects.all().order_by('-ts')[:10]
    
    if not backups:
        print('Резервные копии не найдены')
        return
    
    print('\nДоступные резервные копии:')
    print('-' * 80)
    print(f'{"ID":<5} {"Дата создания":<20} {"Статус":<15} {"Описание":<30}')
    print('-' * 80)
    
    for backup in backups:
        print(f'{backup.id:<5} {str(backup.ts):<20} {backup.status:<15} {backup.description or "":<30}')


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Восстановление базы данных из резервной копии')
    parser.add_argument('backup_id', type=int, nargs='?', help='ID резервной копии для восстановления')
    parser.add_argument('--list', '-l', action='store_true', help='Показать список резервных копий')
    
    args = parser.parse_args()
    
    if args.list:
        list_backups()
        return
    
    if not args.backup_id:
        print('Ошибка: Необходимо указать ID резервной копии')
        print('Используйте --list для просмотра доступных резервных копий')
        sys.exit(1)
    
    success = restore_backup(args.backup_id)
    
    if success:
        print('Восстановление завершено успешно')
        sys.exit(0)
    else:
        print('Ошибка при восстановлении')
        sys.exit(1)


if __name__ == '__main__':
    main()

