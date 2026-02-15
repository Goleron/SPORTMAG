"""
Общие утилиты
"""
from django.db import connection


def execute_db_function(function_name, *args):
    """
    Выполнение хранимой функции PostgreSQL
    
    Args:
        function_name: имя функции в БД
        *args: аргументы функции
    
    Returns:
        результат выполнения функции
    """
    with connection.cursor() as cursor:
        cursor.callproc(function_name, args)
        return cursor.fetchall()


def set_current_user_id(user_id):
    """
    Установка текущего пользователя для использования в триггерах БД
    """
    with connection.cursor() as cursor:
        # В PostgreSQL для установки переменных конфигурации с точкой в имени используется set_config()
        # Параметр 'true' означает, что переменная действует только для текущей транзакции
        cursor.execute("SELECT set_config('app.current_user_id', %s, true)", [str(user_id)])


def set_current_role(role_name):
    """
    Установка текущей роли для использования в триггерах БД
    """
    with connection.cursor() as cursor:
        # В PostgreSQL для установки переменных конфигурации с точкой в имени используется set_config()
        # Параметр 'true' означает, что переменная действует только для текущей транзакции
        cursor.execute("SELECT set_config('app.current_role', %s, true)", [role_name])

