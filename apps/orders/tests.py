"""
Тесты для заказов
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.catalog.models import Category, Product
from apps.accounts.models import Role
from apps.cart.models import CartItem
from .models import Order, Transaction
from .services import OrderService, PaymentService

User = get_user_model()


class OrderAPITestCase(TestCase):
    """Тесты для API заказов"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
        
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role=self.buyer_role
        )
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
    
    def get_admin_token(self):
        """Получить токен администратора"""
        refresh = RefreshToken.for_user(self.admin)
        return str(refresh.access_token)
    
    def test_create_order_from_cart(self):
        """Тест создания заказа из корзины"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        
        # Добавляем товар в корзину
        CartItem.objects.create(
            user=self.buyer,
            product=self.product,
            quantity=2
        )
        
        response = self.client.post('/api/v1/orders/create/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('order', response.data)
        order_id = response.data['order']['id']
        self.assertTrue(Order.objects.filter(id=order_id).exists())
    
    def test_create_order_empty_cart(self):
        """Тест создания заказа с пустой корзиной"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        response = self.client.post('/api/v1/orders/create/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_list_orders_buyer(self):
        """Тест получения списка заказов покупателем"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        
        # Создаем заказ
        order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Pending'
        )
        
        response = self.client.get('/api/v1/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_list_orders_admin(self):
        """Тест получения всех заказов администратором"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        
        Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Pending'
        )
        
        response = self.client.get('/api/v1/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_get_order_detail(self):
        """Тест получения деталей заказа"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        
        order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Pending'
        )
        
        response = self.client.get(f'/api/v1/orders/{order.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], order.id)


class PaymentTestCase(TestCase):
    """Тесты для платежей"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        
        self.order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Pending'
        )
    
    def get_buyer_token(self):
        """Получить токен покупателя"""
        refresh = RefreshToken.for_user(self.buyer)
        return str(refresh.access_token)
    
    def test_create_payment(self):
        """Тест создания платежа"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        data = {
            'amount': '1000.00',
            'payment_method': 'Card',
            'card_number': '4111111111111111',
            'card_expiry': '12/25',
            'card_cvv': '123',
            'cardholder_name': 'Test User'
        }
        response = self.client.post(f'/api/v1/orders/{self.order.id}/pay/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('transaction', response.data)
        
        # Проверяем, что заказ обновлен
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'Completed')


class OrderServiceTestCase(TestCase):
    """Тесты для сервиса заказов"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
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
    
    def test_create_order_from_cart(self):
        """Тест создания заказа из корзины через сервис"""
        CartItem.objects.create(
            user=self.buyer,
            product=self.product,
            quantity=2
        )
        
        order, total_amount = OrderService.create_order_from_cart(self.buyer)
        self.assertIsNotNone(order)
        order = Order.objects.get(id=order.id)
        self.assertEqual(order.user.id, self.buyer.id)
        self.assertEqual(float(total_amount), 2000.00)
    
    def test_get_user_orders(self):
        """Тест получения заказов пользователя"""
        order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Pending'
        )
        
        orders = OrderService.get_user_orders(self.buyer)
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first().id, order.id)

