"""
Тесты для общих функций (безопасность, права доступа, SQL-инъекции)
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import Role
from apps.catalog.models import Category, Product
from .permissions import IsAdmin, IsBuyer, IsAnalyst

User = get_user_model()


class SecurityTestCase(TestCase):
    """Тесты безопасности"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.analyst_role, _ = Role.objects.get_or_create(name='Analyst')
        
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
        self.analyst = User.objects.create_user(
            username='analyst',
            email='analyst@test.com',
            password='testpass123',
            role=self.analyst_role
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
    
    def get_admin_token(self):
        """Получить токен администратора"""
        refresh = RefreshToken.for_user(self.admin)
        return str(refresh.access_token)
    
    def get_buyer_token(self):
        """Получить токен покупателя"""
        refresh = RefreshToken.for_user(self.buyer)
        return str(refresh.access_token)
    
    def get_analyst_token(self):
        """Получить токен аналитика"""
        refresh = RefreshToken.for_user(self.analyst)
        return str(refresh.access_token)
    
    def test_sql_injection_in_search(self):
        """Тест защиты от SQL-инъекций в поиске"""
        # Попытка SQL-инъекции
        malicious_input = "'; DROP TABLE products; --"
        response = self.client.get(f'/api/v1/products/?search={malicious_input}')
        
        # Должен вернуть 200 (поиск не нашел), но не должен выполнить SQL
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Проверяем, что таблица все еще существует
        self.assertTrue(Product.objects.exists())
    
    def test_sql_injection_in_filter(self):
        """Тест защиты от SQL-инъекций в фильтрах"""
        malicious_input = "1 OR 1=1"
        response = self.client.get(f'/api/v1/products/?category={malicious_input}')
        
        # Должен вернуть ошибку или пустой результат, но не выполнить SQL
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        self.assertTrue(Product.objects.exists())
    
    def test_xss_protection(self):
        """Тест защиты от XSS"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        
        # Попытка XSS в названии товара
        xss_payload = "<script>alert('XSS')</script>"
        data = {
            'name': xss_payload,
            'sku': 'XSS-001',
            'price': '1000.00',
            'stock_quantity': 10,
            'category': self.category.id
        }
        response = self.client.post('/api/v1/products/', data)
        
        # Должен создать товар, но скрипт не должен выполниться
        if response.status_code == status.HTTP_201_CREATED:
            product = Product.objects.get(sku='XSS-001')
            # Проверяем, что скрипт экранирован в ответе
            self.assertNotIn('<script>', str(response.data.get('name', '')))


class PermissionsTestCase(TestCase):
    """Тесты прав доступа"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.analyst_role, _ = Role.objects.get_or_create(name='Analyst')
        
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
        self.analyst = User.objects.create_user(
            username='analyst',
            email='analyst@test.com',
            password='testpass123',
            role=self.analyst_role
        )
    
    def get_admin_token(self):
        """Получить токен администратора"""
        refresh = RefreshToken.for_user(self.admin)
        return str(refresh.access_token)
    
    def get_buyer_token(self):
        """Получить токен покупателя"""
        refresh = RefreshToken.for_user(self.buyer)
        return str(refresh.access_token)
    
    def get_analyst_token(self):
        """Получить токен аналитика"""
        refresh = RefreshToken.for_user(self.analyst)
        return str(refresh.access_token)
    
    def test_admin_access_to_users(self):
        """Тест доступа администратора к управлению пользователями"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_buyer_no_access_to_users(self):
        """Тест запрета доступа покупателя к управлению пользователями"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_analyst_access_to_analytics(self):
        """Тест доступа аналитика к аналитике"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_analyst_token()}')
        response = self.client.get('/api/v1/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_buyer_no_access_to_analytics(self):
        """Тест запрета доступа покупателя к аналитике"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        response = self.client.get('/api/v1/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_access_to_backups(self):
        """Тест доступа администратора к бэкапам"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        response = self.client.get('/api/v1/admin/backups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_buyer_no_access_to_backups(self):
        """Тест запрета доступа покупателя к бэкапам"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        response = self.client.get('/api/v1/admin/backups/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PasswordHashingTestCase(TestCase):
    """Тесты хеширования паролей"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
    
    def test_password_is_hashed(self):
        """Тест, что пароль хранится в захешированном виде"""
        password = 'testpass123'
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password=password,
            role=self.buyer_role
        )
        
        # Пароль не должен быть в открытом виде
        self.assertNotEqual(user.password, password)
        # Пароль должен быть длинным хешем
        self.assertGreater(len(user.password), 50)
    
    def test_password_verification(self):
        """Тест проверки пароля"""
        password = 'testpass123'
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password=password,
            role=self.buyer_role
        )
        
        # Проверяем правильный пароль
        self.assertTrue(user.check_password(password))
        # Проверяем неправильный пароль
        self.assertFalse(user.check_password('wrongpassword'))


class CardDataSecurityTestCase(TestCase):
    """Тесты безопасности данных карт"""
    
    def test_card_data_not_in_logs(self):
        """Тест, что полные данные карты не попадают в логи"""
        from apps.common.models import Log
        from apps.common.card_utils import sanitize_card_data
        
        card_number = "4111111111111111"
        card_cvv = "123"
        
        sanitized = sanitize_card_data(card_number, card_cvv)
        
        # Проверяем, что полные данные не присутствуют
        self.assertNotIn("4111111111111111", str(sanitized))
        self.assertNotIn("123", str(sanitized))
        self.assertEqual(sanitized.get('card_cvv'), '***')
    
    def test_saved_cards_masked(self):
        """Тест, что сохраненные карты маскируются"""
        from apps.common.card_utils import mask_card_number
        from apps.accounts.models import Role
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role=buyer_role
        )
        
        # Добавляем карту
        user.add_saved_card('hash123', '1111', 'Test User')
        
        # Получаем сохраненные карты
        cards = user.get_saved_cards()
        
        # Проверяем, что хеш не возвращается в открытом виде
        for card in cards:
            self.assertNotIn('hash', card)  # Хеш не должен быть в ответе
            self.assertIn('last_four', card)  # Только последние 4 цифры
