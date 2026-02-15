"""
Админ-панель для заказов
"""
from django.contrib import admin
from .models import Order, OrderItem, Transaction


class OrderItemInline(admin.TabularInline):
    """Инлайн для позиций заказа"""
    model = OrderItem
    extra = 0
    readonly_fields = ('price_at_purchase', 'created_at')
    fields = ('product', 'quantity', 'price_at_purchase')


class TransactionInline(admin.TabularInline):
    """Инлайн для транзакций"""
    model = Transaction
    extra = 0
    readonly_fields = ('transaction_date', 'created_at', 'updated_at')
    fields = ('amount', 'payment_method', 'status', 'transaction_date')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Админ-панель для заказов"""
    list_display = ('id', 'user', 'total_amount', 'status', 'order_date', 'created_at')
    list_filter = ('status', 'order_date', 'created_at')
    search_fields = ('id', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'order_date')
    inlines = [OrderItemInline, TransactionInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'total_amount', 'status', 'order_date')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Админ-панель для позиций заказа"""
    list_display = ('id', 'order', 'product', 'quantity', 'price_at_purchase', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order__id', 'product__name', 'product__sku')
    readonly_fields = ('created_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Админ-панель для транзакций"""
    list_display = ('id', 'order', 'amount', 'payment_method', 'status', 'transaction_date')
    list_filter = ('status', 'payment_method', 'transaction_date')
    search_fields = ('order__id',)
    readonly_fields = ('transaction_date', 'created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('order', 'amount', 'payment_method', 'status', 'transaction_date')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

