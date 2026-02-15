"""
Приложение каталога: категории, товары, атрибуты, импорт/экспорт.
"""
from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.catalog'

