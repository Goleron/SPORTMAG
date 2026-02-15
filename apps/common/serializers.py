"""
Сериализаторы для логов и аудита
"""
from rest_framework import serializers
from .models import Log, AuditLog, Backup, BackupSchedule
from apps.accounts.serializers import UserListSerializer


class LogSerializer(serializers.ModelSerializer):
    """Сериализатор для лога"""
    user = UserListSerializer(read_only=True)
    
    class Meta:
        model = Log
        fields = ('id', 'ts', 'level', 'message', 'user', 'ip_address', 'meta')
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    """Сериализатор для записи аудита"""
    user = UserListSerializer(read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True, allow_null=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = (
            'id', 'ts', 'user', 'user_username', 'user_id', 'action', 'action_display',
            'table_name', 'record_id', 'old_data', 'new_data', 'query_meta'
        )
        read_only_fields = fields


class BackupSerializer(serializers.ModelSerializer):
    """Сериализатор для резервной копии"""
    created_by = UserListSerializer(read_only=True)
    
    class Meta:
        model = Backup
        fields = ('id', 'ts', 'file_path', 'created_by', 'status', 'description')
        read_only_fields = fields


class CreateBackupSerializer(serializers.Serializer):
    """Сериализатор для создания резервной копии"""
    description = serializers.CharField(required=False, allow_blank=True, max_length=500)


class BackupScheduleSerializer(serializers.ModelSerializer):
    """Сериализатор для расписания бекапов"""
    updated_by = UserListSerializer(read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    
    class Meta:
        model = BackupSchedule
        fields = (
            'id', 'is_enabled', 'frequency', 'frequency_display',
            'time', 'keep_days', 'last_run', 'updated_by', 'updated_at'
        )
        read_only_fields = ('id', 'last_run', 'updated_by', 'updated_at')

