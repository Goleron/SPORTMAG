"""
Эндпоинты каталога: категории, товары, атрибуты.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Prefetch
from .models import Category, Product, Attribute, ProductAttributeValue
from .serializers import (
    CategorySerializer,
    CategoryTreeSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    AttributeSerializer,
    ProductAttributeValueSerializer,
    ProductAttributeValueWriteSerializer
)
from .services import ProductService, CategoryService
from ..common.permissions import IsAdmin, IsBuyer


class CategoryListAPIView(generics.ListCreateAPIView):
    """Список категорий и создание (Admin)"""
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['parent']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Оптимизированный queryset с prefetch для счетчиков"""
        return Category.objects.select_related('parent').prefetch_related(
            'children',
            'products'
        ).all()
    
    def get_permissions(self):
        """Разные права для GET и POST"""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdmin()]


class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление и удаление категории"""
    serializer_class = CategorySerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        """Оптимизированный queryset с prefetch"""
        return Category.objects.select_related('parent').prefetch_related(
            'children',
            'products'
        ).all()
    
    def get_permissions(self):
        """Разные права для GET и остальных методов"""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdmin()]


class CategoryTreeAPIView(generics.ListAPIView):
    """Дерево категорий"""
    queryset = CategoryService.get_category_tree()
    serializer_class = CategoryTreeSerializer
    permission_classes = [permissions.AllowAny]


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def category_products_view(request, pk):
    """
    Товары в категории
    
    GET /api/v1/categories/{id}/products/
    """
    category = CategoryService.get_category_with_products(pk)
    if not category:
        return Response(
            {'error': 'Категория не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    products = ProductService.get_products_with_filters(
        category_id=pk,
        available_only=True
    )
    
    serializer = ProductListSerializer(products, many=True)
    return Response(serializer.data)


class ProductListAPIView(generics.ListCreateAPIView):
    """Список товаров и создание (Admin)"""
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_available']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'name', 'created_at', 'stock_quantity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        category_params = self.request.query_params.getlist('category')
        category_id = None
        for param in category_params:
            try:
                category_id = int(param)
                break  # Используем первое валидное числовое значение
            except (ValueError, TypeError):
                continue
        search = self.request.query_params.get('search', None)
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        in_stock_only = self.request.query_params.get('in_stock', 'false').lower() == 'true'
        available_only = self.request.query_params.get('available_only', 'true').lower() == 'true'
        ordering = self.request.query_params.get('ordering', '-created_at')
        
        return ProductService.get_products_with_filters(
            category_id=category_id,
            search=search,
            min_price=float(min_price) if min_price else None,
            max_price=float(max_price) if max_price else None,
            in_stock_only=in_stock_only,
            available_only=available_only,
            ordering=ordering
        )
    
    def get_serializer_class(self):
        """Разные сериализаторы для GET и POST"""
        if self.request.method == 'POST':
            return ProductDetailSerializer
        return ProductListSerializer
    
    def get_permissions(self):
        """Разные права для GET и POST"""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdmin()]


class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление и удаление товара"""
    serializer_class = ProductDetailSerializer
    lookup_field = 'pk'
    lookup_url_kwarg = 'pk'
    
    def get_queryset(self):
        """Получение queryset с оптимизацией"""
        queryset = Product.objects.select_related('category').prefetch_related(
            Prefetch(
                'attribute_values',
                queryset=ProductAttributeValue.objects.select_related('attribute')
            )
        ).all()
        return queryset
    
    def get_object(self):
        """Получение объекта товара"""
        import logging
        logger = logging.getLogger(__name__)
        
        pk = self.kwargs.get('pk')
        logger.info(f'ProductDetailAPIView.get_object called with pk={pk}, kwargs={self.kwargs}')
        
        if not pk:
            from rest_framework.exceptions import NotFound
            raise NotFound('ID товара не указан')
        
        try:
            queryset = self.get_queryset()
            logger.info(f'Queryset count: {queryset.count()}')
            obj = queryset.get(pk=pk)
            logger.info(f'Product found: {obj.id} - {obj.name}')
            return obj
        except Product.DoesNotExist:
            logger.warning(f'Product with pk={pk} not found')
            from rest_framework.exceptions import NotFound
            raise NotFound(f'Товар с ID {pk} не найден')
        except (ValueError, TypeError) as e:
            logger.error(f'Invalid pk value: {pk}, error: {e}')
            from rest_framework.exceptions import NotFound
            raise NotFound('Неверный ID товара')
    
    def get_permissions(self):
        """Разные права для GET и остальных методов"""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdmin()]
    
    def handle_exception(self, exc):
        """Обработка исключений для возврата JSON вместо HTML"""
        from rest_framework.views import exception_handler
        response = exception_handler(exc, self)
        if response is not None:
            return response
        return super().handle_exception(exc)


class AttributeListAPIView(generics.ListCreateAPIView):
    """Список атрибутов и создание (Admin)"""
    queryset = Attribute.objects.all()
    serializer_class = AttributeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        """Разные права для GET и POST"""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdmin()]


class AttributeDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление и удаление атрибута"""
    queryset = Attribute.objects.all()
    serializer_class = AttributeSerializer
    
    def get_permissions(self):
        """Разные права для GET и остальных методов"""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdmin()]


class ProductAttributeListAPIView(generics.ListCreateAPIView):
    """Список атрибутов товара"""
    serializer_class = ProductAttributeValueSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        """Получение атрибутов конкретного товара"""
        product_id = self.kwargs['product_id']
        return ProductAttributeValue.objects.filter(
            product_id=product_id
        ).select_related('attribute')
    
    def get_serializer_class(self):
        """Разные сериализаторы для GET и POST"""
        if self.request.method == 'POST':
            return ProductAttributeValueWriteSerializer
        return ProductAttributeValueSerializer
    
    def perform_create(self, serializer):
        """Создание атрибута товара"""
        product_id = self.kwargs['product_id']
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Товар не найден')
        
        serializer.save(product=product)


class ProductAttributeDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление и удаление атрибута товара"""
    serializer_class = ProductAttributeValueSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        """Получение атрибутов конкретного товара"""
        product_id = self.kwargs['product_id']
        return ProductAttributeValue.objects.filter(
            product_id=product_id
        ).select_related('attribute')

