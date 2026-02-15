#!/usr/bin/env python
"""
Скрипт для автоматического создания резервных копий базы данных
"""
import os
import sys
import django
from datetime import datetime
import subprocess

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.db import connection


def create_backup(description=None):
    """
    Создать резервную копию базы данных
    
    Args:
        description: Описание резервной копии
    
    Returns:
        str: Путь к созданному файлу резервной копии
    """
    # Получаем настройки БД
    db_settings = settings.DATABASES['default']
    
    db_name = db_settings['NAME']
    db_user = db_settings['USER']
    db_password = db_settings.get('PASSWORD', '')
    db_host = db_settings.get('HOST', 'localhost')
    db_port = db_settings.get('PORT', '5432')
    
    # Создаем имя файла с датой и временем
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'shop_backup_{timestamp}.sql'
    
    # Путь для сохранения бэкапов
    backup_dir = getattr(settings, 'BACKUP_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups'))
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, backup_filename)
    
    # Создаем команду pg_dump
    env = os.environ.copy()
    if db_password:
        env['PGPASSWORD'] = db_password
    
    cmd = [
        'pg_dump',
        '-h', db_host,
        '-p', str(db_port),
        '-U', db_user,
        '-d', db_name,
        '-F', 'c',  # Custom format
        '-f', backup_path
    ]
    
    print(f'Создание резервной копии: {backup_path}')
    
    # Выполняем pg_dump
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 минут таймаут
        )
        
        if result.returncode != 0:
            print(f'Ошибка создания резервной копии: {result.stderr}')
            return None
        
        print(f'Резервная копия успешно создана: {backup_path}')
        
        # Создаем запись в БД через функцию create_backup
        with connection.cursor() as cursor:
            cursor.callproc('create_backup', [1, description or None])  # user_id=1 для системных бэкапов
            result = cursor.fetchone()
            backup_id = result[0] if result else None
        
        # Обновляем путь к файлу в записи
        if backup_id:
            from apps.common.models import Backup
            backup = Backup.objects.get(id=backup_id)
            backup.file_path = backup_path
            backup.save()
            print(f'Запись в БД создана: ID={backup_id}')
        
        return backup_path
        
    except subprocess.TimeoutExpired:
        print('Ошибка: Превышено время ожидания при создании резервной копии')
        return None
    except Exception as e:
        print(f'Ошибка создания резервной копии: {e}')
        return None


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Создание резервной копии базы данных')
    parser.add_argument('--description', '-d', help='Описание резервной копии')
    
    args = parser.parse_args()
    
    backup_path = create_backup(args.description)
    
    if backup_path:
        print('Резервное копирование завершено успешно')
        sys.exit(0)
    else:
        print('Ошибка при создании резервной копии')
        sys.exit(1)


if __name__ == '__main__':
    main()

