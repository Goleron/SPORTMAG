"""
Регистрация моделей каталога в админке Django.
"""
from django.contrib import admin
from .models import Category, Product, Attribute, ProductAttributeValue


class CategoryAdmin(admin.ModelAdmin):
    """Админ-панель для категорий"""
    list_display = ('name', 'slug', 'parent', 'created_at')
    list_filter = ('parent', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class ProductAttributeValueInline(admin.TabularInline):
    """Инлайн для значений атрибутов товара"""
    model = ProductAttributeValue
    extra = 1
    fields = ('attribute', 'value')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Админ-панель для товаров"""
    list_display = ('name', 'sku', 'category', 'price', 'stock_quantity', 'is_available', 'created_at')
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductAttributeValueInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'sku', 'category', 'description', 'image_url')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'stock_quantity', 'is_available')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    """Админ-панель для атрибутов"""
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    """Админ-панель для значений атрибутов"""
    list_display = ('product', 'attribute', 'value', 'created_at')
    list_filter = ('attribute', 'created_at')
    search_fields = ('product__name', 'attribute__name', 'value')
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(Category, CategoryAdmin)

