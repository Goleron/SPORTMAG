"""
Тесты API корзины и сервиса CartService.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.catalog.models import Category, Product
from apps.accounts.models import Role
from .models import CartItem
from .services import CartService

User = get_user_model()


class CartAPITestCase(TestCase):
    """Тесты для API корзины"""
    
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
    
    def test_get_cart_authenticated(self):
        """Тест получения корзины авторизованным пользователем"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        response = self.client.get('/api/v1/cart/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_get_cart_unauthenticated(self):
        """Тест получения корзины неавторизованным пользователем"""
        response = self.client.get('/api/v1/cart/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_add_to_cart(self):
        """Тест добавления товара в корзину"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        data = {
            'product_id': self.product.id,
            'quantity': 2
        }
        response = self.client.post('/api/v1/cart/items/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CartItem.objects.filter(user=self.buyer, product=self.product).exists())
    
    def test_update_cart_item(self):
        """Тест обновления количества товара в корзине"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        cart_item = CartItem.objects.create(
            user=self.buyer,
            product=self.product,
            quantity=1
        )
        data = {'quantity': 3}
        response = self.client.put(f'/api/v1/cart/items/{cart_item.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)
    
    def test_remove_from_cart(self):
        """Тест удаления товара из корзины"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        cart_item = CartItem.objects.create(
            user=self.buyer,
            product=self.product,
            quantity=1
        )
        response = self.client.delete(f'/api/v1/cart/items/{cart_item.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())


class CartServiceTestCase(TestCase):
    """Тесты для сервиса корзины"""
    
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
    
    def test_add_item_to_cart(self):
        """Тест добавления товара в корзину через сервис"""
        cart_item = CartService.add_to_cart(self.buyer, self.product.id, 2)
        self.assertIsNotNone(cart_item)
        self.assertEqual(cart_item.quantity, 2)
    
    def test_get_cart_items(self):
        """Тест получения элементов корзины"""
        CartItem.objects.create(
            user=self.buyer,
            product=self.product,
            quantity=1
        )
        
        items = CartService.get_cart(self.buyer)
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().product.id, self.product.id)
    
    def test_validate_cart_items(self):
        """Тест валидации элементов корзины"""
        CartItem.objects.create(
            user=self.buyer,
            product=self.product,
            quantity=15
        )
        
        is_valid, errors = CartService.validate_cart(self.buyer)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

