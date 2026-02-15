"""
Модели для логов и аудита
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Log(models.Model):
    """Операционные логи системы"""
    id = models.BigAutoField(primary_key=True)
    ts = models.DateTimeField(auto_now_add=True, db_column='ts', verbose_name='Время')
    level = models.CharField(max_length=10, verbose_name='Уровень')
    message = models.TextField(verbose_name='Сообщение')
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='user_id',
        related_name='logs',
        verbose_name='Пользователь'
    )
    ip_address = models.CharField(max_length=50, null=True, blank=True, verbose_name='IP адрес')
    meta = models.JSONField(default=dict, blank=True, null=True, verbose_name='Метаданные')
    
    class Meta:
        db_table = 'logs'
        verbose_name = 'Лог'
        verbose_name_plural = 'Логи'
        ordering = ['-ts']
        indexes = [
            models.Index(fields=['user', 'ts'], name='idx_logs_user_ts'),
        ]
    
    def __str__(self):
        return f"{self.level}: {self.message[:50]}"


class AuditLog(models.Model):
    """Журнал аудита изменений"""
    ACTION_CHOICES = [
        ('CREATE', 'Создание'),
        ('UPDATE', 'Обновление'),
        ('DELETE', 'Удаление'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    ts = models.DateTimeField(auto_now_add=True, db_column='ts', verbose_name='Время')
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='user_id',
        related_name='audit_logs',
        verbose_name='Пользователь'
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name='Действие')
    table_name = models.TextField(verbose_name='Таблица')
    record_id = models.TextField(null=True, blank=True, verbose_name='ID записи')
    old_data = models.JSONField(default=dict, blank=True, null=True, verbose_name='Старые данные')
    new_data = models.JSONField(default=dict, blank=True, null=True, verbose_name='Новые данные')
    query_meta = models.JSONField(default=dict, blank=True, null=True, verbose_name='Метаданные запроса')
    
    class Meta:
        db_table = 'audit_log'
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-ts']
        indexes = [
            models.Index(fields=['table_name', 'ts'], name='idx_audit_table_ts'),
            models.Index(fields=['user', 'ts'], name='idx_audit_user_ts'),
            models.Index(fields=['action', 'ts'], name='idx_audit_action_ts'),
        ]
    
    def __str__(self):
        return f"{self.action} {self.table_name} #{self.record_id}"


class Backup(models.Model):
    """Метаданные резервных копий"""
    id = models.BigAutoField(primary_key=True)
    ts = models.DateTimeField(auto_now_add=True, db_column='ts', verbose_name='Время создания')
    file_path = models.TextField(verbose_name='Путь к файлу')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='created_by',
        related_name='backups',
        verbose_name='Создано пользователем'
    )
    status = models.CharField(max_length=30, verbose_name='Статус')
    description = models.TextField(null=True, blank=True, verbose_name='Описание')
    
    class Meta:
        db_table = 'backups'
        verbose_name = 'Резервная копия'
        verbose_name_plural = 'Резервные копии'
        ordering = ['-ts']
    
    def __str__(self):
        return f"Backup {self.id} - {self.status}"


class BackupSchedule(models.Model):
    """Настройки автоматического резервного копирования"""
    FREQUENCY_CHOICES = [
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
    ]
    
    id = models.AutoField(primary_key=True)
    is_enabled = models.BooleanField(default=False, verbose_name='Включено')
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default='daily',
        verbose_name='Частота'
    )
    time = models.TimeField(default='02:00', verbose_name='Время запуска')
    keep_days = models.IntegerField(default=30, verbose_name='Хранить дней')
    last_run = models.DateTimeField(null=True, blank=True, verbose_name='Последний запуск')
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backup_schedule_updates',
        verbose_name='Обновлено пользователем'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        db_table = 'backup_schedule'
        verbose_name = 'Расписание бекапов'
        verbose_name_plural = 'Расписание бекапов'
    
    def __str__(self):
        status = 'Включено' if self.is_enabled else 'Отключено'
        return f"Расписание бекапов ({status}, {self.get_frequency_display()}, {self.time})"
