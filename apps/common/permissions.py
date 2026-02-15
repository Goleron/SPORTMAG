"""
Кастомные permissions для управления доступом
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Только администраторы"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role.name == 'Admin'
        )


class IsAnalyst(permissions.BasePermission):
    """Аналитики и администраторы"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role.name in ('Analyst', 'Admin')
        )


class IsBuyer(permissions.BasePermission):
    """Покупатели и выше (все авторизованные)"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Владелец ресурса или администратор"""
    
    def has_object_permission(self, request, view, obj):
        # Администратор имеет доступ ко всему
        if hasattr(request.user, 'role') and request.user.role.name == 'Admin':
            return True
        
        # Проверяем, является ли пользователь владельцем
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
        elif hasattr(obj, 'user'):
            return obj.user.id == request.user.id
        
        return False

