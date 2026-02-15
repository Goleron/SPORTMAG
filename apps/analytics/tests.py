"""
Тесты API аналитики и сервиса отчётов.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
from apps.catalog.models import Category, Product
from apps.accounts.models import Role
from apps.orders.models import Order, OrderItem
from .services import AnalyticsService

User = get_user_model()


class AnalyticsAPITestCase(TestCase):
    """Тесты для API аналитики"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        self.analyst_role, _ = Role.objects.get_or_create(name='Analyst')
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        
        self.analyst = User.objects.create_user(
            username='analyst',
            email='analyst@test.com',
            password='testpass123',
            role=self.analyst_role
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
            name='Товар',
            sku='PROD-001',
            price=1000.00,
            stock_quantity=10,
            category=self.category,
            is_available=True
        )
        self.order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Completed',
            order_date=timezone.now()
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
    
    def get_analyst_token(self):
        """Получить токен аналитика"""
        refresh = RefreshToken.for_user(self.analyst)
        return str(refresh.access_token)
    
    def get_buyer_token(self):
        """Получить токен покупателя"""
        refresh = RefreshToken.for_user(self.buyer)
        return str(refresh.access_token)
    
    def test_dashboard_stats_analyst(self):
        """Тест получения статистики дашборда аналитиком"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_analyst_token()}')
        response = self.client.get('/api/v1/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_revenue', response.data)
        self.assertIn('total_orders', response.data)
    
    def test_dashboard_stats_buyer_forbidden(self):
        """Тест запрета доступа к аналитике покупателем"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        response = self.client.get('/api/v1/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_sales_by_product(self):
        """Тест получения продаж по продуктам"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_analyst_token()}')
        response = self.client.get('/api/v1/analytics/sales-by-product/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_monthly_sales(self):
        """Тест получения ежемесячных продаж"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_analyst_token()}')
        response = self.client.get('/api/v1/analytics/monthly-sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_top_products(self):
        """Тест получения топ товаров"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_analyst_token()}')
        response = self.client.get('/api/v1/analytics/top-products/?limit=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_revenue(self):
        """Тест получения выручки"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_analyst_token()}')
        date_from = (timezone.now() - timedelta(days=30)).date().isoformat()
        date_to = timezone.now().date().isoformat()
        response = self.client.get(f'/api/v1/analytics/revenue/?date_from={date_from}&date_to={date_to}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_export_sales_by_product_csv(self):
        """Тест экспорта продаж по продуктам в CSV"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_analyst_token()}')
        response = self.client.get('/api/v1/analytics/sales-by-product/export/csv/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
    
    def test_export_top_products_csv(self):
        """Тест экспорта топ товаров в CSV"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_analyst_token()}')
        response = self.client.get('/api/v1/analytics/top-products/export/csv/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')


class AnalyticsServiceTestCase(TestCase):
    """Тесты для сервиса аналитики"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.category = Category.objects.create(
            name='Категория',
            slug='category'
        )
        self.product = Product.objects.create(
            name='Товар',
            sku='PROD-001',
            price=1000.00,
            stock_quantity=10,
            category=self.category,
            is_available=True
        )
        
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Completed',
            order_date=timezone.now()
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
    
    def test_get_sales_by_product(self):
        """Тест получения продаж по продуктам"""
        results = AnalyticsService.get_sales_by_product()
        self.assertIsInstance(results, list)
        if results:
            self.assertIn('product_id', results[0])
            self.assertIn('total_revenue', results[0])
    
    def test_get_top_products(self):
        """Тест получения топ товаров"""
        results = AnalyticsService.get_top_products(limit=10)
        self.assertIsInstance(results, list)
    
    def test_get_monthly_sales(self):
        """Тест получения ежемесячных продаж"""
        results = AnalyticsService.get_monthly_sales()
        self.assertIsInstance(results, list)

