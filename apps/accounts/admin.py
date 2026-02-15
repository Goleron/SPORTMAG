"""
Регистрация моделей User и Role в админке Django.
"""
from django.contrib import admin
from .models import User, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Админ-панель для ролей"""
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Админ-панель для пользователей"""
    list_display = ('username', 'email', 'role', 'is_active', 'last_login', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('username', 'email')
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('email',)}),
        ('Права доступа', {'fields': ('role', 'is_active')}),
        ('Настройки', {'fields': ('settings',)}),
        ('Важные даты', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password', 'role', 'is_active'),
        }),
    )
    
    ordering = ('-created_at',)
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(obj.password)
        elif 'password' in form.changed_data:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)

