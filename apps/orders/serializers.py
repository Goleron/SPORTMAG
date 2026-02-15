"""
Сериализаторы для заказов
"""
from rest_framework import serializers
from .models import Order, OrderItem, Transaction, Chat, ChatMessage
from .validators import (
    validate_payment_amount, validate_card_number, 
    validate_card_expiry, validate_cvv
)
from apps.catalog.serializers import ProductListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор для позиции заказа"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = (
            'id', 'product', 'product_id', 'product_name',
            'quantity', 'price_at_purchase', 'total_price', 'created_at'
        )
        read_only_fields = fields

    def get_total_price(self, obj):
        """Общая стоимость позиции"""
        return float(obj.get_total_price())


class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор для заказа"""
    items = OrderItemSerializer(many=True, read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    can_be_paid = serializers.SerializerMethodField()
    can_be_refunded = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    transactions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = (
            'id', 'user', 'user_username', 'user_email',
            'total_amount', 'status', 'order_date', 'delivery_address',
            'items', 'can_be_paid', 'can_be_refunded', 'is_active',
            'transactions_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'order_date')
    
    def get_can_be_paid(self, obj):
        """Можно ли оплатить заказ"""
        return obj.can_be_paid()
    
    def get_can_be_refunded(self, obj):
        """Можно ли вернуть заказ"""
        return obj.can_be_refunded()
    
    def get_is_active(self, obj):
        """Является ли заказ активным"""
        return obj.is_active()
    
    def get_transactions_count(self, obj):
        """Количество транзакций"""
        return obj.transactions.count()


class OrderListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка заказов"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = (
            'id', 'user', 'user_username', 'total_amount',
            'status', 'order_date', 'delivery_address', 'items_count', 'created_at'
        )
        read_only_fields = fields
    
    def get_items_count(self, obj):
        """Количество позиций в заказе"""
        return obj.items.count()


class TransactionSerializer(serializers.ModelSerializer):
    """Сериализатор для транзакции"""
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_total = serializers.DecimalField(source='order.total_amount', max_digits=14, decimal_places=2, read_only=True)
    can_be_refunded = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = (
            'id', 'order', 'order_id', 'order_total',
            'amount', 'payment_method', 'status',
            'transaction_date', 'can_be_refunded',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'transaction_date', 'created_at', 'updated_at')
    
    def get_can_be_refunded(self, obj):
        """Можно ли вернуть транзакцию"""
        return obj.can_be_refunded()


class CreateOrderSerializer(serializers.Serializer):
    """Сериализатор для создания заказа из корзины"""
    # Заказ создается из корзины, поэтому дополнительных полей не требуется
    pass


class CreatePaymentSerializer(serializers.Serializer):
    """Сериализатор для создания платежа"""
    amount = serializers.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        required=True,
        validators=[validate_payment_amount]
    )
    payment_method = serializers.ChoiceField(
        choices=Transaction.PAYMENT_METHOD_CHOICES,
        required=True
    )
    card_number = serializers.CharField(
        max_length=19, 
        required=False, 
        write_only=True,
        validators=[validate_card_number]
    )
    card_expiry = serializers.CharField(
        max_length=7, 
        required=False, 
        write_only=True,
        validators=[validate_card_expiry]
    )  # MM/YYYY
    card_cvv = serializers.CharField(
        max_length=4, 
        required=False, 
        write_only=True,
        validators=[validate_cvv]
    )
    cardholder_name = serializers.CharField(max_length=100, required=False, write_only=True)
    save_card = serializers.BooleanField(default=False, required=False, write_only=True)
    use_saved_card = serializers.CharField(max_length=255, required=False, write_only=True, help_text='Хеш сохраненной карты')
    delivery_address = serializers.CharField(
        max_length=500,
        required=True,
        write_only=True,
        help_text='Адрес доставки для курьера',
        allow_blank=False
    )
    
    def validate(self, attrs):
        """Дополнительная валидация"""
        payment_method = attrs.get('payment_method')
        card_number = attrs.get('card_number')
        use_saved_card = attrs.get('use_saved_card')
        
        # Если способ оплаты - карта, требуем либо данные карты, либо хеш сохраненной карты
        if payment_method == 'Card':
            if not card_number and not use_saved_card:
                raise serializers.ValidationError({
                    'card_number': 'Номер карты обязателен для оплаты картой, либо используйте сохраненную карту'
                })
            # Если используется сохраненная карта, не требуем данные новой карты
            if use_saved_card and card_number:
                raise serializers.ValidationError({
                    'card_number': 'Нельзя использовать сохраненную карту и новую карту одновременно'
                })
        
        return attrs


class ChatMessageSerializer(serializers.ModelSerializer):
    """Сериализатор для сообщения чата"""
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_role = serializers.CharField(source='sender.role.name', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = (
            'id', 'chat', 'sender', 'sender_username', 'sender_role',
            'message', 'created_at', 'is_read'
        )
        read_only_fields = ('id', 'created_at', 'is_read')


class ChatSerializer(serializers.ModelSerializer):
    """Сериализатор для чата"""
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    messages = ChatMessageSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = (
            'id', 'order', 'order_id', 'order_status',
            'user', 'user_username', 'messages', 'unread_count',
            'created_at', 'updated_at', 'is_active'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_unread_count(self, obj):
        """Количество непрочитанных сообщений"""
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0


class CreateChatMessageSerializer(serializers.Serializer):
    """Сериализатор для создания сообщения в чате"""
    message = serializers.CharField(required=True, max_length=2000)
