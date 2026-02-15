#!/usr/bin/env python
"""
Скрипт для проверки целостности данных в базе данных
"""
import os
import sys
import django
import json

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.common.data_integrity import DataIntegrityChecker


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Проверка целостности данных в базе данных')
    parser.add_argument(
        '--json',
        action='store_true',
        help='Вывести результат в формате JSON'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Проверка целостности данных")
    print("=" * 60)
    print()
    
    result = DataIntegrityChecker.run_all_checks()
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Статус: {result['status']}")
        print(f"Всего проблем: {result['total_issues']}")
        print()
        
        if result['total_issues'] > 0:
            print("Найденные проблемы:")
            print("-" * 60)
            
            for issue in result['all_issues']:
                print(f"\n{issue['type']}: {issue['message']}")
                if args.verbose and 'details' in issue:
                    print("Детали:")
                    for detail in issue['details'][:5]:  # Показываем первые 5
                        print(f"  - {detail}")
                    if len(issue['details']) > 5:
                        print(f"  ... и еще {len(issue['details']) - 5}")
        else:
            print("✓ Проблем не найдено. Данные целостны.")
        
        print()
        print("=" * 60)
    
    sys.exit(0 if result['total_issues'] == 0 else 1)


if __name__ == '__main__':
    main()

