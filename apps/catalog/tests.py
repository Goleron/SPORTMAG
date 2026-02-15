"""
Тесты API каталога, сервисов и импорта/экспорта.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Category, Product
from apps.accounts.models import Role

User = get_user_model()


class CategoryAPITestCase(TestCase):
    """Тесты для API категорий"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        # Создаем роли
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        
        # Создаем пользователей
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=self.admin_role
        )
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category',
            description='Описание категории'
        )
    
    def get_admin_token(self):
        """Получить токен администратора"""
        refresh = RefreshToken.for_user(self.admin)
        return str(refresh.access_token)
    
    def get_buyer_token(self):
        """Получить токен покупателя"""
        refresh = RefreshToken.for_user(self.buyer)
        return str(refresh.access_token)
    
    def test_list_categories_anonymous(self):
        """Тест получения списка категорий без авторизации"""
        response = self.client.get('/api/v1/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_category_admin(self):
        """Тест создания категории администратором"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        data = {
            'name': 'Новая категория',
            'slug': 'new-category',
            'description': 'Описание'
        }
        response = self.client.post('/api/v1/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name='Новая категория').exists())
    
    def test_create_category_buyer_forbidden(self):
        """Тест запрета создания категории покупателем"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        data = {
            'name': 'Новая категория',
            'slug': 'new-category'
        }
        response = self.client.post('/api/v1/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_category_admin(self):
        """Тест обновления категории администратором"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        data = {'name': 'Обновленная категория'}
        response = self.client.put(f'/api/v1/categories/{self.category.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Обновленная категория')
    
    def test_delete_category_admin(self):
        """Тест удаления категории администратором"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        response = self.client.delete(f'/api/v1/categories/{self.category.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=self.category.id).exists())


class ProductAPITestCase(TestCase):
    """Тесты для API товаров"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=self.admin_role
        )
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        self.category = Category.objects.create(
            name='Категория',
            slug='category'
        )
        self.product = Product.objects.create(
            name='Тестовый товар',
            sku='TEST-001',
            price=1000.00,
            stock_quantity=10,
            category=self.category,
            is_available=True
        )
    
    def get_admin_token(self):
        """Получить токен администратора"""
        refresh = RefreshToken.for_user(self.admin)
        return str(refresh.access_token)
    
    def get_buyer_token(self):
        """Получить токен покупателя"""
        refresh = RefreshToken.for_user(self.buyer)
        return str(refresh.access_token)
    
    def test_list_products_anonymous(self):
        """Тест получения списка товаров без авторизации"""
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_search_products(self):
        """Тест поиска товаров"""
        response = self.client.get('/api/v1/products/?search=Тестовый')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data.get('results', [])), 0)
    
    def test_filter_products_by_category(self):
        """Тест фильтрации товаров по категории"""
        response = self.client.get(f'/api/v1/products/?category={self.category.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        if results:
            self.assertEqual(results[0]['category'], self.category.id)
    
    def test_create_product_admin(self):
        """Тест создания товара администратором"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        data = {
            'name': 'Новый товар',
            'sku': 'NEW-001',
            'price': '2000.00',
            'stock_quantity': 5,
            'category': self.category.id,
            'is_available': True
        }
        response = self.client.post('/api/v1/products/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(sku='NEW-001').exists())
    
    def test_create_product_buyer_forbidden(self):
        """Тест запрета создания товара покупателем"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        data = {
            'name': 'Новый товар',
            'sku': 'NEW-002',
            'price': '2000.00',
            'stock_quantity': 5
        }
        response = self.client.post('/api/v1/products/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_product_admin(self):
        """Тест обновления товара администратором"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        data = {'price': '1500.00'}
        response = self.client.put(f'/api/v1/products/{self.product.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(float(self.product.price), 1500.00)
    
    def test_get_product_detail(self):
        """Тест получения деталей товара"""
        response = self.client.get(f'/api/v1/products/{self.product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Тестовый товар')


class ProductServiceTestCase(TestCase):
    """Тесты для сервиса товаров"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.category = Category.objects.create(
            name='Категория',
            slug='category'
        )
        self.product1 = Product.objects.create(
            name='Товар 1',
            sku='PROD-001',
            price=1000.00,
            stock_quantity=10,
            category=self.category,
            is_available=True
        )
        self.product2 = Product.objects.create(
            name='Товар 2',
            sku='PROD-002',
            price=2000.00,
            stock_quantity=0,
            category=self.category,
            is_available=False
        )
    
    def test_get_products_with_filters(self):
        """Тест получения товаров с фильтрами"""
        from .services import ProductService
        products = ProductService.get_products_with_filters(category_id=self.category.id)
        self.assertEqual(products.count(), 2)
        products = ProductService.get_products_with_filters(available_only=True)
        self.assertEqual(products.count(), 1)
        self.assertEqual(products.first().name, 'Товар 1')
        products = ProductService.get_products_with_filters(search='Товар 1')
        self.assertEqual(products.count(), 1)
        self.assertEqual(products.first().name, 'Товар 1')
    
    def test_check_availability(self):
        """Тест проверки наличия товара"""
        from .services import ProductService
        available, product = ProductService.check_availability(self.product1.id, 5)
        self.assertTrue(available)
        self.assertEqual(product.stock_quantity, 10)
        available, product = ProductService.check_availability(self.product2.id, 5)
        self.assertFalse(available)
        self.assertEqual(product.stock_quantity, 0)


class ProductImportExportTestCase(TestCase):
    """Тесты для импорта/экспорта товаров"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=self.admin_role
        )
        
        self.category = Category.objects.create(
            name='Категория',
            slug='category'
        )
    
    def get_admin_token(self):
        """Получить токен администратора"""
        refresh = RefreshToken.for_user(self.admin)
        return str(refresh.access_token)
    
    def test_export_products_csv(self):
        """Тест экспорта товаров в CSV"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        response = self.client.get('/api/v1/products/export/csv/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])

