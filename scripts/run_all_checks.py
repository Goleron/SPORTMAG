#!/usr/bin/env python
"""
Скрипт для запуска всех проверок системы
"""
import os
import sys
import django
import subprocess

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


def run_check_normalization():
    """Запуск проверки нормализации БД"""
    print("\n" + "=" * 60)
    print("1. Проверка нормализации БД (3НФ)")
    print("=" * 60)
    result = subprocess.run(
        [sys.executable, 'scripts/check_normalization.py'],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0


def run_data_integrity_check():
    """Запуск проверки целостности данных"""
    print("\n" + "=" * 60)
    print("2. Проверка целостности данных")
    print("=" * 60)
    result = subprocess.run(
        [sys.executable, 'scripts/check_data_integrity.py'],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0


def main():
    """Главная функция"""
    print("=" * 60)
    print("Комплексная проверка системы")
    print("=" * 60)
    
    results = []
    
    # Проверка нормализации
    results.append(('Нормализация БД', run_check_normalization()))
    
    # Проверка целостности данных
    results.append(('Целостность данных', run_data_integrity_check()))
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ ПРОЙДЕНО" if passed else "✗ ОШИБКИ"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("Все проверки пройдены успешно!")
        sys.exit(0)
    else:
        print("Обнаружены проблемы. Проверьте вывод выше.")
        sys.exit(1)


if __name__ == '__main__':
    main()

