"""
Сервисы каталога: товары и категории с фильтрами и кэшированием.
"""
from django.db.models import Q, Prefetch, Count
from django.core.cache import cache
from .models import Product, Category, Attribute, ProductAttributeValue


class ProductService:
    CACHE_TIMEOUT_POPULAR = 1800
    CACHE_KEY_POPULAR = 'popular_products'
    
    @staticmethod
    def get_popular_products(limit=12):
        """
        Получение популярных товаров с кэшированием
        
        Args:
            limit: количество товаров
        
        Returns:
            QuerySet товаров
        """
        cache_key = f"{ProductService.CACHE_KEY_POPULAR}_{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        products = Product.objects.filter(
            is_available=True,
            stock_quantity__gt=0
        ).annotate(
            sales_count=Count('order_items')
        ).select_related('category').prefetch_related(
            Prefetch(
                'attribute_values',
                queryset=ProductAttributeValue.objects.select_related('attribute')
            )
        ).order_by('-sales_count', '-created_at')[:limit]
        
        cache.set(cache_key, products, ProductService.CACHE_TIMEOUT_POPULAR)
        return products
    
    @staticmethod
    def invalidate_cache():
        for limit in [6, 12, 24, 48]:
            cache.delete(f"{ProductService.CACHE_KEY_POPULAR}_{limit}")
    
    @staticmethod
    def get_products_with_filters(
        category_id=None,
        search=None,
        min_price=None,
        max_price=None,
        in_stock_only=False,
        available_only=False,
        ordering='-created_at'
    ):
        """
        Получение товаров с фильтрацией
        
        Args:
            category_id: ID категории
            search: поисковый запрос
            min_price: минимальная цена
            max_price: максимальная цена
            in_stock_only: только товары в наличии
            available_only: только доступные товары
            ordering: сортировка
        
        Returns:
            QuerySet товаров
        """
        queryset = Product.objects.select_related('category').prefetch_related(
            Prefetch(
                'attribute_values',
                queryset=ProductAttributeValue.objects.select_related('attribute')
            )
        ).all()
        if category_id:
            category_ids = [category_id]
            category = Category.objects.filter(id=category_id).first()
            if category:
                children = category.children.all()
                category_ids.extend([c.id for c in children])
            queryset = queryset.filter(category_id__in=category_ids)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(sku__icontains=search)
            )
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        if in_stock_only:
            queryset = queryset.filter(stock_quantity__gt=0)
        
        if available_only:
            queryset = queryset.filter(is_available=True)
        queryset = queryset.order_by(ordering)
        
        return queryset
    
    @staticmethod
    def get_product_by_id(product_id):
        """Получение товара по ID с оптимизацией запросов"""
        try:
            return Product.objects.select_related('category').prefetch_related(
                Prefetch(
                    'attribute_values',
                    queryset=ProductAttributeValue.objects.select_related('attribute')
                )
            ).get(id=product_id, is_available=True)
        except Product.DoesNotExist:
            return None
    
    @staticmethod
    def check_availability(product_id, quantity):
        """
        Проверка доступности товара в нужном количестве
        
        Args:
            product_id: ID товара
            quantity: требуемое количество
        
        Returns:
            tuple: (is_available, product) или (False, None)
        """
        try:
            product = Product.objects.get(id=product_id, is_available=True)
            if product.stock_quantity >= quantity:
                return True, product
            return False, product
        except Product.DoesNotExist:
            return False, None


class CategoryService:
    CACHE_TIMEOUT = 3600
    CACHE_KEY_TREE = 'category_tree'
    CACHE_KEY_LIST = 'category_list'
    
    @staticmethod
    def get_category_tree():
        """Получение дерева категорий с кэшированием"""
        cached = cache.get(CategoryService.CACHE_KEY_TREE)
        if cached is not None:
            return cached
        
        root_categories = Category.objects.filter(parent=None).prefetch_related('children').all()
        cache.set(CategoryService.CACHE_KEY_TREE, root_categories, CategoryService.CACHE_TIMEOUT)
        return root_categories
    
    @staticmethod
    def get_all_categories():
        """Получение всех категорий с кэшированием"""
        cached = cache.get(CategoryService.CACHE_KEY_LIST)
        if cached is not None:
            return cached
        
        categories = Category.objects.all().order_by('name')
        cache.set(CategoryService.CACHE_KEY_LIST, categories, CategoryService.CACHE_TIMEOUT)
        return categories
    
    @staticmethod
    def invalidate_cache():
        """Инвалидация кэша категорий"""
        cache.delete(CategoryService.CACHE_KEY_TREE)
        cache.delete(CategoryService.CACHE_KEY_LIST)
    
    @staticmethod
    def get_category_with_products(category_id):
        """Получение категории с товарами"""
        try:
            return Category.objects.prefetch_related('products').get(id=category_id)
        except Category.DoesNotExist:
            return None

