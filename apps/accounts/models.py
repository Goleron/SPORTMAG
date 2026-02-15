"""
Модели пользователей и ролей (User, Role) и менеджеры.
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator
import json


class RoleManager(models.Manager):
    """Менеджер для модели Role"""
    pass


class Role(models.Model):
    """Роль пользователя"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    objects = RoleManager()
    
    class Meta:
        db_table = 'roles'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    """Менеджер для модели User"""
    
    def create_user(self, username, email, password=None, role_name='Buyer', **extra_fields):
        """
        Создание обычного пользователя
        
        Внимание: для регистрации используйте UserService.register_user(),
        который вызывает функцию БД register_user() для правильного хеширования пароля через crypt.
        Этот метод используется только для создания пользователей вручную (например, через админку).
        """
        if not email:
            raise ValueError('Email обязателен')
        if not username:
            raise ValueError('Username обязателен')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            raise ValueError(f'Роль {role_name} не найдена')
        
        user.role = role
        
        if password:
            user.set_password(password)
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """Создание суперпользователя"""
        extra_fields.setdefault('is_active', True)
        role = Role.objects.get_or_create(name='Admin', defaults={'description': 'Администратор системы'})[0]
        extra_fields['role'] = role
        
        return self.create_user(username, email, password, role_name='Admin', **extra_fields)


class User(AbstractBaseUser):
    """Пользователь системы"""
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True, verbose_name='Имя пользователя')
    email = models.EmailField(max_length=255, unique=True, verbose_name='Email')
    password = models.CharField(max_length=128, verbose_name='Хеш пароля', db_column='password_hash')
    role = models.ForeignKey(
        Role,
        on_delete=models.RESTRICT,
        db_column='role_id',
        related_name='users',
        verbose_name='Роль'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='Последний вход')
    settings = models.JSONField(default=dict, blank=True, verbose_name='Настройки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username
    
    @property
    def is_staff(self):
        """Является ли пользователь администратором"""
        return self.role.name == 'Admin' if self.role else False
    
    @property
    def is_superuser(self):
        """Является ли пользователь суперпользователем"""
        return self.is_staff
    
    def has_perm(self, perm, obj=None):
        """Проверка прав доступа"""
        return self.is_staff
    
    def has_module_perms(self, app_label):
        """Проверка прав на модуль"""
        return self.is_staff
    
    def get_settings(self):
        """Получить настройки пользователя"""
        if isinstance(self.settings, str):
            return json.loads(self.settings)
        return self.settings or {}
    
    def set_setting(self, key, value):
        """Установить настройку"""
        settings = self.get_settings()
        settings[key] = value
        self.settings = settings
        self.save(update_fields=['settings'])
    
    def get_saved_cards(self):
        """Получить сохраненные карты (хешированные)"""
        settings = self.get_settings()
        return settings.get('saved_cards', [])
    
    def add_saved_card(self, card_hash, last_four, cardholder_name):
        """
        Добавить сохраненную карту (только хеш)
        
        Args:
            card_hash: хеш данных карты (используя crypt)
            last_four: последние 4 цифры карты
            cardholder_name: имя держателя карты
        """
        import hashlib
        settings = self.get_settings()
        if 'saved_cards' not in settings:
            settings['saved_cards'] = []
        
        for card in settings['saved_cards']:
            if card.get('hash') == card_hash:
                return False
        
        settings['saved_cards'].append({
            'hash': card_hash,
            'last_four': last_four,
            'cardholder_name': cardholder_name,
            'added_at': str(self.updated_at)
        })
        self.settings = settings
        self.save(update_fields=['settings'])
        return True
    
    def remove_saved_card(self, card_hash):
        """Удалить сохраненную карту"""
        settings = self.get_settings()
        if 'saved_cards' not in settings:
            return False
        
        settings['saved_cards'] = [
            card for card in settings['saved_cards']
            if card.get('hash') != card_hash
        ]
        self.settings = settings
        self.save(update_fields=['settings'])
        return True

