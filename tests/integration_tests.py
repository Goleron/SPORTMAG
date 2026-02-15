"""
Интеграционные тесты для полного цикла операций
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from apps.catalog.models import Category, Product
from apps.accounts.models import Role
from apps.cart.models import CartItem
from apps.orders.models import Order

User = get_user_model()


class FullOrderCycleTestCase(TestCase):
    """Тест полного цикла создания заказа"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        Role.objects.get_or_create(name='Buyer')
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role_name='Buyer'
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
    
    def get_buyer_token(self):
        """Получить токен покупателя"""
        refresh = RefreshToken.for_user(self.buyer)
        return str(refresh.access_token)
    
    def test_full_order_cycle(self):
        """Тест полного цикла: добавление в корзину -> создание заказа -> оплата"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        
        # 1. Добавляем товар в корзину
        cart_data = {
            'product_id': self.product.id,
            'quantity': 2
        }
        cart_response = self.client.post('/api/v1/cart/items/', cart_data)
        self.assertEqual(cart_response.status_code, status.HTTP_201_CREATED)
        
        # 2. Создаем заказ из корзины
        order_response = self.client.post('/api/v1/orders/create/')
        self.assertEqual(order_response.status_code, status.HTTP_201_CREATED)
        order_id = order_response.data['order']['id']
        
        # 3. Создаем платеж
        payment_data = {
            'amount': '2000.00',
            'payment_method': 'Card',
            'card_number': '4111111111111111',
            'card_expiry': '12/2025',
            'card_cvv': '123',
            'cardholder_name': 'Test User',
            'delivery_address': 'Тестовый адрес доставки, д. 1',
        }
        payment_response = self.client.post(f'/api/v1/orders/{order_id}/pay/', payment_data)
        self.assertEqual(payment_response.status_code, status.HTTP_201_CREATED)
        
        # 4. Проверяем, что заказ завершен
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, 'Completed')
        
        # 5. Проверяем, что корзина очищена
        cart_items = CartItem.objects.filter(user=self.buyer)
        self.assertEqual(cart_items.count(), 0)


class ImportExportTestCase(TestCase):
    """Тесты импорта/экспорта данных"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        Role.objects.get_or_create(name='Admin')
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role_name='Admin'
        )
        
        self.category = Category.objects.create(
            name='Категория',
            slug='category'
        )
    
    def get_admin_token(self):
        """Получить токен администратора"""
        refresh = RefreshToken.for_user(self.admin)
        return str(refresh.access_token)
    
    def test_import_export_products(self):
        """Тест импорта и экспорта товаров"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        
        # 1. Экспортируем товары
        export_response = self.client.get('/api/v1/products/export/csv/')
        self.assertEqual(export_response.status_code, status.HTTP_200_OK)
        
        # 2. Импортируем товары из CSV
        import csv
        import io
        
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(['SKU', 'Название', 'Описание', 'Категория', 'Цена', 'Количество на складе', 'Доступен'])
        writer.writerow(['IMPORT-001', 'Импортированный товар', 'Описание', self.category.name, '1500.00', '5', 'да'])
        
        csv_file = io.BytesIO(csv_data.getvalue().encode('utf-8-sig'))
        csv_file.name = 'test_import.csv'
        
        import_response = self.client.post(
            '/api/v1/products/import/csv/',
            {'file': csv_file},
            format='multipart'
        )
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        
        # 3. Проверяем, что товар создан
        from apps.catalog.models import Product
        self.assertTrue(Product.objects.filter(sku='IMPORT-001').exists())

