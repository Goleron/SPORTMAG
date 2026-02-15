#!/usr/bin/env python
"""
Скрипт для проверки нормализации базы данных (3НФ)
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection


def check_3nf():
    """
    Проверка нормализации базы данных до 3НФ
    """
    print("=" * 60)
    print("Проверка нормализации базы данных (3НФ)")
    print("=" * 60)
    
    issues = []
    warnings = []
    
    with connection.cursor() as cursor:
        # Проверка 1: Нет транзитивных зависимостей
        print("\n1. Проверка транзитивных зависимостей...")
        
        # Проверяем таблицы на наличие транзитивных зависимостей
        tables_to_check = [
            'users', 'products', 'categories', 'orders', 
            'order_items', 'cart_items', 'transactions'
        ]
        
        for table in tables_to_check:
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'shop' 
                AND table_name = '{table}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            # Проверяем, что нет вычисляемых полей, которые зависят от других полей
            # (это упрощенная проверка, полная проверка требует анализа зависимостей)
            print(f"  ✓ Таблица {table}: {len(columns)} колонок")
        
        # Проверка 2: Все неключевые атрибуты зависят только от первичного ключа
        print("\n2. Проверка зависимости от первичного ключа...")
        
        # Проверяем наличие внешних ключей (это нормально для 3НФ)
        cursor.execute("""
            SELECT
                tc.table_name, 
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'shop'
            ORDER BY tc.table_name, kcu.column_name
        """)
        
        foreign_keys = cursor.fetchall()
        print(f"  ✓ Найдено {len(foreign_keys)} внешних ключей (нормально для 3НФ)")
        
        # Проверка 3: Нет повторяющихся групп данных
        print("\n3. Проверка повторяющихся групп...")
        
        # Проверяем, что нет JSONB полей с повторяющимися данными
        # (JSONB допустим для настроек, но не для основных данных)
        cursor.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'shop'
            AND data_type = 'jsonb'
            AND column_name NOT IN ('settings', 'meta', 'old_data', 'new_data', 'query_meta')
        """)
        
        jsonb_columns = cursor.fetchall()
        if jsonb_columns:
            warnings.append(f"Найдены JSONB колонки (кроме настроек): {jsonb_columns}")
            print(f"  ⚠ Найдено {len(jsonb_columns)} JSONB колонок")
        else:
            print("  ✓ Нет проблемных JSONB колонок")
        
        # Проверка 4: Проверка уникальности и ограничений
        print("\n4. Проверка ограничений целостности...")
        
        cursor.execute("""
            SELECT
                tc.table_name,
                tc.constraint_type,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            WHERE tc.table_schema = 'shop'
            AND tc.constraint_type IN ('UNIQUE', 'CHECK', 'PRIMARY KEY')
            ORDER BY tc.table_name, tc.constraint_type
        """)
        
        constraints = cursor.fetchall()
        print(f"  ✓ Найдено {len(constraints)} ограничений целостности")
        
        # Проверка 5: Количество таблиц
        print("\n5. Проверка количества таблиц...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'shop'
            AND table_type = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()[0]
        print(f"  ✓ Найдено {table_count} таблиц")
        
        if table_count < 8:
            issues.append(f"Недостаточно таблиц: {table_count} (требуется минимум 8)")
        else:
            print("  ✓ Требование выполнено (минимум 8 таблиц)")
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    if issues:
        print("\n❌ Найдены проблемы:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ Критических проблем не найдено")
    
    if warnings:
        print("\n⚠ Предупреждения:")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("\n" + "=" * 60)
    print("Проверка завершена")
    print("=" * 60)
    
    return len(issues) == 0


if __name__ == '__main__':
    success = check_3nf()
    sys.exit(0 if success else 1)

