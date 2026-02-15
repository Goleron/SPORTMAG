"""
Модель элемента корзины (CartItem).
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from apps.catalog.models import Product

User = get_user_model()


class CartItem(models.Model):
    """Элемент корзины"""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cart_items',
        db_column='user_id',
        verbose_name='Пользователь'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.RESTRICT,
        related_name='cart_items',
        db_column='product_id',
        verbose_name='Товар'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Количество'
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        db_table = 'cart_items'
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = [['user', 'product']]
        indexes = [
            models.Index(fields=['user']),
        ]
        ordering = ['-added_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.product.name} x{self.quantity}'
    
    def get_total_price(self):
        """Получить общую стоимость позиции"""
        return self.product.price * self.quantity
    
    def can_increase(self, amount=1):
        """Проверка возможности увеличения количества"""
        return self.product.stock_quantity >= (self.quantity + amount)
    
    def increase_quantity(self, amount=1):
        """Увеличить количество товара"""
        new_quantity = self.quantity + amount
        if not self.can_increase(amount):
            raise ValueError(
                f'Недостаточно товара на складе. Доступно: {self.product.stock_quantity}, '
                f'запрошено: {new_quantity}'
            )
        self.quantity = new_quantity
        self.save(update_fields=['quantity', 'updated_at'])

