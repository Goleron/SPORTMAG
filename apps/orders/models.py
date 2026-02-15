"""
Модели заказов, позиций заказа, транзакций и чата поддержки.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from apps.catalog.models import Product

User = get_user_model()


class Order(models.Model):
    """Заказ"""
    STATUS_CHOICES = [
        ('Pending', 'Ожидает оплаты'),
        ('Processing', 'В обработке'),
        ('Shipped', 'Отправлен'),
        ('Delivered', 'Доставлен'),
        ('Completed', 'Завершен'),
        ('Refunded', 'Возвращен'),
        ('Cancelled', 'Отменен'),
    ]
    
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='orders',
        db_column='user_id',
        verbose_name='Пользователь'
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Общая сумма'
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='Pending',
        verbose_name='Статус'
    )
    order_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата заказа')
    delivery_address = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Адрес доставки',
        help_text='Адрес доставки, который будет использован курьером'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        db_table = 'orders'
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['order_date']),
        ]
        ordering = ['-order_date']
    
    def __str__(self):
        return f'Заказ #{self.id} от {self.user.username} - {self.total_amount} руб.'
    
    def can_be_paid(self):
        return self.status in ['Pending', 'Cancelled']
    
    def can_be_refunded(self):
        """Можно ли вернуть заказ"""
        return self.status == 'Completed'
    
    def is_active(self):
        """Является ли заказ активным (не завершен и не отменен)"""
        return self.status not in ['Completed', 'Cancelled', 'Refunded']


class OrderItem(models.Model):
    """Позиция заказа"""
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='order_id',
        verbose_name='Заказ'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.RESTRICT,
        related_name='order_items',
        db_column='product_id',
        verbose_name='Товар'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Количество'
    )
    price_at_purchase = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Цена на момент покупки'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        db_table = 'order_items'
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'
        ordering = ['created_at']
    
    def __str__(self):
        return f'{self.order} - {self.product.name} x{self.quantity}'
    
    def get_total_price(self):
        """Получить общую стоимость позиции"""
        return self.price_at_purchase * self.quantity


class Transaction(models.Model):
    """Транзакция оплаты"""
    STATUS_CHOICES = [
        ('Success', 'Успешно'),
        ('Failed', 'Неудачно'),
        ('Refunded', 'Возвращено'),
        ('Pending', 'Ожидает'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('Card', 'Карта'),
        ('Cash', 'Наличные'),
        ('Online', 'Онлайн'),
        ('Bank Transfer', 'Банковский перевод'),
    ]
    
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='transactions',
        db_column='order_id',
        verbose_name='Заказ'
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Сумма'
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='Способ оплаты'
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        verbose_name='Статус'
    )
    transaction_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата транзакции')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_date']),
        ]
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f'Транзакция #{self.id} - {self.amount} руб. ({self.status})'
    
    def can_be_refunded(self):
        """Можно ли вернуть транзакцию"""
        return self.status == 'Success'


class Chat(models.Model):
    """Чат между пользователем и аналитиком/админом"""
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='chats',
        db_column='order_id',
        verbose_name='Заказ'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_chats',
        db_column='user_id',
        verbose_name='Пользователь'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    class Meta:
        db_table = 'chats'
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'Чат для заказа #{self.order.id}'
    
    def get_participants(self):
        """Получить участников чата"""
        participants = [self.user]
        # Добавляем аналитиков и админов, которые участвовали в чате
        messages = self.messages.all()
        for message in messages:
            if message.sender not in participants:
                participants.append(message.sender)
        return participants


class ChatMessage(models.Model):
    """Сообщение в чате"""
    id = models.AutoField(primary_key=True)
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='messages',
        db_column='chat_id',
        verbose_name='Чат'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        db_column='sender_id',
        verbose_name='Отправитель'
    )
    message = models.TextField(verbose_name='Сообщение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    
    class Meta:
        db_table = 'chat_messages'
        verbose_name = 'Сообщение чата'
        verbose_name_plural = 'Сообщения чатов'
        indexes = [
            models.Index(fields=['chat']),
            models.Index(fields=['sender']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f'Сообщение от {self.sender.username} в чате #{self.chat.id}'
