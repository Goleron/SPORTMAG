"""
Сериализаторы элементов корзины для DRF API.
"""
from rest_framework import serializers
from .models import CartItem
from apps.catalog.serializers import ProductListSerializer


class CartItemSerializer(serializers.ModelSerializer):
    """Сериализатор для элемента корзины"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total_price = serializers.SerializerMethodField()
    can_increase = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = (
            'id', 'product', 'product_id', 'quantity',
            'total_price', 'can_increase', 'added_at', 'updated_at'
        )
        read_only_fields = ('id', 'added_at', 'updated_at')
    
    def get_total_price(self, obj):
        """Общая стоимость позиции"""
        return float(obj.get_total_price())
    
    def get_can_increase(self, obj):
        """Можно ли увеличить количество"""
        return obj.can_increase()
    
    def validate_product_id(self, value):
        """Проверка существования товара и его доступности"""
        from apps.catalog.models import Product
        try:
            product = Product.objects.get(id=value, is_available=True)
            if product.stock_quantity == 0:
                raise serializers.ValidationError('Товар отсутствует на складе')
        except Product.DoesNotExist:
            raise serializers.ValidationError('Товар не найден или недоступен')
        return value
    
    def validate_quantity(self, value):
        """Проверка количества"""
        if value < 1:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value
    
    def validate(self, attrs):
        """Проверка наличия товара на складе"""
        product_id = attrs.get('product_id')
        quantity = attrs.get('quantity', 1)
        
        if product_id:
            from apps.catalog.models import Product
            try:
                product = Product.objects.get(id=product_id)
                if product.stock_quantity < quantity:
                    raise serializers.ValidationError(
                        f'Недостаточно товара на складе. Доступно: {product.stock_quantity}'
                    )
            except Product.DoesNotExist:
                pass
        return attrs


class CartItemAddSerializer(serializers.Serializer):
    """Сериализатор для добавления товара в корзину"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    
    def validate_product_id(self, value):
        """Проверка существования товара"""
        from apps.catalog.models import Product
        try:
            product = Product.objects.get(id=value, is_available=True)
            if product.stock_quantity == 0:
                raise serializers.ValidationError('Товар отсутствует на складе')
        except Product.DoesNotExist:
            raise serializers.ValidationError('Товар не найден или недоступен')
        return value
    
    def validate(self, attrs):
        """Проверка наличия товара на складе"""
        product_id = attrs.get('product_id')
        quantity = attrs.get('quantity', 1)
        
        from apps.catalog.models import Product
        product = Product.objects.get(id=product_id)
        
        if product.stock_quantity < quantity:
            raise serializers.ValidationError(
                f'Недостаточно товара на складе. Доступно: {product.stock_quantity}'
            )
        
        return attrs


class CartSerializer(serializers.Serializer):
    """Сериализатор для полной корзины"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

