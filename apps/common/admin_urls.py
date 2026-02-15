"""
Маршруты админ-API: логи, аудит, бэкапы, проверка целостности данных.
"""
from django.urls import path
from . import admin_views

app_name = 'api_admin'

urlpatterns = [
    path('logs/', admin_views.LogListAPIView.as_view(), name='log-list'),
    path('audit/', admin_views.AuditLogListAPIView.as_view(), name='audit-list'),
    path('backups/', admin_views.BackupListAPIView.as_view(), name='backup-list'),
    path('backups/create/', admin_views.create_backup_view, name='backup-create'),
    path('backups/schedule/', admin_views.backup_schedule_view, name='backup-schedule'),
    path('backups/<int:backup_id>/download/', admin_views.download_backup_view, name='backup-download'),
    path('backups/<int:backup_id>/restore/', admin_views.restore_backup_view, name='backup-restore'),
    path('integrity/check/', admin_views.check_data_integrity_view, name='integrity-check'),
]

