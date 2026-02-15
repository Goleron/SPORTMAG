#!/usr/bin/env python
"""
Скрипт для очистки старых резервных копий
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.conf import settings


def cleanup_old_backups(days_to_keep=30):
    """
    Удалить резервные копии старше указанного количества дней
    
    Args:
        days_to_keep: Количество дней для хранения бэкапов (по умолчанию 30)
    """
    backup_dir = getattr(settings, 'BACKUP_DIR', os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'backups'
    ))
    
    if not os.path.exists(backup_dir):
        print(f'Директория {backup_dir} не существует')
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    deleted_count = 0
    total_size = 0
    
    print(f'Удаление резервных копий старше {days_to_keep} дней (до {cutoff_date.strftime("%Y-%m-%d")})')
    
    for file_path in Path(backup_dir).glob('shop_backup_*.sql'):
        file_stat = file_path.stat()
        file_date = datetime.fromtimestamp(file_stat.st_mtime)
        
        if file_date < cutoff_date:
            file_size = file_stat.st_size
            total_size += file_size
            try:
                file_path.unlink()
                deleted_count += 1
                print(f'Удален: {file_path.name} ({file_size / 1024 / 1024:.2f} MB)')
            except Exception as e:
                print(f'Ошибка при удалении {file_path.name}: {e}')
    
    print(f'\nУдалено файлов: {deleted_count}')
    print(f'Освобождено места: {total_size / 1024 / 1024:.2f} MB')


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Очистка старых резервных копий')
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Количество дней для хранения бэкапов (по умолчанию 30)'
    )
    
    args = parser.parse_args()
    
    # Настраиваем Django только для получения settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    
    cleanup_old_backups(args.days)


if __name__ == '__main__':
    main()

