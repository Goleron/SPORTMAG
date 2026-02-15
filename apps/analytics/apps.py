"""
Приложение аналитики: отчёты по продажам, выручке, дашборд.
"""
from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.analytics'

