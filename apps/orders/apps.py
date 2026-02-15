"""
Приложение заказов: создание, оплата, транзакции, чат с поддержкой.
"""
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'

