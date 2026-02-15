"""
Сериализаторы категорий, товаров и атрибутов для DRF API.
"""
from rest_framework import serializers
from .models import Category, Product, Attribute, ProductAttributeValue


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категории"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    children_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = (
            'id', 'name', 'slug', 'description', 'parent', 'parent_name',
            'children_count', 'products_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_children_count(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'children' in obj._prefetched_objects_cache:
            return len(obj.children.all())
        return obj.children.count()
    
    def get_products_count(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'products' in obj._prefetched_objects_cache:
            return len(obj.products.all())
        return obj.products.count()


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Сериализатор для дерева категорий"""
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'children')
    
    def get_children(self, obj):
        """Рекурсивное получение дочерних категорий"""
        children = obj.children.all()
        return CategoryTreeSerializer(children, many=True).data


class AttributeSerializer(serializers.ModelSerializer):
    """Сериализатор для атрибута"""
    
    class Meta:
        model = Attribute
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    """Сериализатор для значения атрибута товара"""
    attribute_name = serializers.CharField(source='attribute.name', read_only=True)
    attribute_id = serializers.IntegerField(source='attribute.id', read_only=True)
    
    class Meta:
        model = ProductAttributeValue
        fields = ('id', 'attribute_id', 'attribute_name', 'value', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProductAttributeValueWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для записи значения атрибута"""
    
    class Meta:
        model = ProductAttributeValue
        fields = ('attribute', 'value')
    
    def validate(self, attrs):
        """Проверка уникальности комбинации product, attribute, value"""
        product = self.context.get('product')
        if product:
            if ProductAttributeValue.objects.filter(
                product=product,
                attribute=attrs['attribute'],
                value=attrs['value']
            ).exists():
                raise serializers.ValidationError(
                    'Такое значение атрибута уже существует для этого товара'
                )
        return attrs


class ProductListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка товаров"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    is_in_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = (
            'id', 'sku', 'name', 'description', 'price', 'stock_quantity',
            'category', 'category_name', 'category_slug',
            'image_url', 'is_available', 'is_in_stock', 'created_at'
        )
        read_only_fields = fields
    
    def get_is_in_stock(self, obj):
        """Проверка наличия товара"""
        return obj.is_in_stock()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор для товара"""
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False)
    attribute_values = ProductAttributeValueSerializer(
        many=True,
        read_only=True
    )
    is_in_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = (
            'id', 'sku', 'name', 'description', 'price', 'stock_quantity',
            'category', 'category_id', 'image_url', 'is_available',
            'is_in_stock', 'attribute_values', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_is_in_stock(self, obj):
        """Проверка наличия товара"""
        return obj.is_in_stock()
    
    def update(self, instance, validated_data):
        """Обновление товара"""
        category_id = validated_data.pop('category_id', None)
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                instance.category = category
            except Category.DoesNotExist:
                raise serializers.ValidationError({'category_id': 'Категория не найдена'})
        
        return super().update(instance, validated_data)

