"""
Админ-панель для моделей common
"""
from django.contrib import admin
from .models import Log, AuditLog, Backup


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('id', 'ts', 'level', 'message', 'user', 'ip_address')
    list_filter = ('level', 'ts', 'user')
    search_fields = ('message', 'ip_address')
    readonly_fields = ('id', 'ts', 'level', 'message', 'user', 'ip_address', 'meta')
    date_hierarchy = 'ts'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'ts', 'action', 'table_name', 'record_id', 'user')
    list_filter = ('action', 'table_name', 'ts', 'user')
    search_fields = ('table_name', 'record_id')
    readonly_fields = ('id', 'ts', 'user', 'action', 'table_name', 'record_id', 'old_data', 'new_data', 'query_meta')
    date_hierarchy = 'ts'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = ('id', 'ts', 'file_path', 'status', 'created_by', 'description')
    list_filter = ('status', 'ts', 'created_by')
    search_fields = ('file_path', 'description')
    readonly_fields = ('id', 'ts', 'file_path', 'created_by', 'status', 'description')
    date_hierarchy = 'ts'

