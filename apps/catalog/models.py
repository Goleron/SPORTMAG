"""
Модели каталога: Category, Product, Attribute, ProductAttributeValue.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify


class Category(models.Model):
    """Категория товаров (с поддержкой иерархии)"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150, verbose_name='Название')
    slug = models.SlugField(max_length=150, unique=True, verbose_name='URL-адрес')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        db_column='parent_id',
        verbose_name='Родительская категория'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Автоматическое создание slug из названия и инвалидация кэша"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        from .services import CategoryService
        CategoryService.invalidate_cache()
    
    def delete(self, *args, **kwargs):
        """Инвалидация кэша при удалении"""
        from .services import CategoryService
        CategoryService.invalidate_cache()
        super().delete(*args, **kwargs)
    
    def get_full_path(self):
        """Получить полный путь категории (с родителями)"""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return ' > '.join(path)


class Attribute(models.Model):
    """Атрибут товара (EAV модель)"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True, verbose_name='Название')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        db_table = 'attributes'
        verbose_name = 'Атрибут'
        verbose_name_plural = 'Атрибуты'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар"""
    id = models.AutoField(primary_key=True)
    sku = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name='Артикул')
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Цена'
    )
    stock_quantity = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='Количество на складе'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        db_column='category_id',
        verbose_name='Категория'
    )
    image_url = models.URLField(blank=True, null=True, verbose_name='URL изображения')
    is_available = models.BooleanField(default=True, verbose_name='Доступен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    attributes = models.ManyToManyField(
        Attribute,
        through='ProductAttributeValue',
        related_name='products',
        verbose_name='Атрибуты'
    )
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_available', 'stock_quantity']),
        ]
    
    def __str__(self):
        return self.name
    
    def is_in_stock(self):
        """Проверка наличия товара на складе"""
        return self.stock_quantity > 0 and self.is_available
    
    def decrease_stock(self, quantity):
        """Уменьшить количество товара на складе"""
        if self.stock_quantity < quantity:
            raise ValueError(f'Недостаточно товара. Доступно: {self.stock_quantity}, запрошено: {quantity}')
        
        self.stock_quantity -= quantity
        if self.stock_quantity == 0:
            self.is_available = False
        self.save(update_fields=['stock_quantity', 'is_available'])
    
    def increase_stock(self, quantity):
        """Увеличить количество товара на складе"""
        self.stock_quantity += quantity
        if not self.is_available:
            self.is_available = True
        self.save(update_fields=['stock_quantity', 'is_available'])
    
    def save(self, *args, **kwargs):
        """Сохранение товара с инвалидацией кэша"""
        super().save(*args, **kwargs)
        from .services import ProductService
        ProductService.invalidate_cache()
    
    def delete(self, *args, **kwargs):
        """Удаление товара с инвалидацией кэша"""
        from .services import ProductService
        ProductService.invalidate_cache()
        super().delete(*args, **kwargs)


class ProductAttributeValue(models.Model):
    """Значение атрибута для товара (EAV)"""
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='attribute_values',
        db_column='product_id',
        verbose_name='Товар'
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='product_values',
        db_column='attribute_id',
        verbose_name='Атрибут'
    )
    value = models.CharField(max_length=255, verbose_name='Значение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        db_table = 'product_attribute_values'
        verbose_name = 'Значение атрибута товара'
        verbose_name_plural = 'Значения атрибутов товаров'
        unique_together = [['product', 'attribute', 'value']]
    
    def __str__(self):
        return f'{self.product.name} - {self.attribute.name}: {self.value}'

