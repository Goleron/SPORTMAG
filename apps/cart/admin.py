"""
Регистрация модели CartItem в админке Django.
"""
from django.contrib import admin
from .models import CartItem


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Админ-панель для элементов корзины"""
    list_display = ('user', 'product', 'quantity', 'added_at', 'updated_at')
    list_filter = ('added_at', 'updated_at')
    search_fields = ('user__username', 'product__name', 'product__sku')
    readonly_fields = ('added_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'product', 'quantity')
        }),
        ('Метаданные', {
            'fields': ('added_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

