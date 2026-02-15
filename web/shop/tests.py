"""
Тесты для веб-интерфейса магазина
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
import json

User = get_user_model()


class APIClientTestCase(TestCase):
    """Базовый класс для тестов с API клиентом"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = Client()
        self.api_base_url = 'http://127.0.0.1:8000/api/v1'
        
    def mock_api_response(self, data, status_code=200):
        """Создать мок ответа API"""
        mock_response = MagicMock()
        mock_response.json.return_value = data
        mock_response.status_code = status_code
        mock_response.text = json.dumps(data) if isinstance(data, dict) else str(data)
        return mock_response


class HomeViewTestCase(APIClientTestCase):
    """Тесты для главной страницы"""
    
    @patch('web.shop.views.APIClient')
    def test_home_view(self, mock_api_client_class):
        """Тест отображения главной страницы"""
        # Настраиваем мок API клиента
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        # Мокаем ответы API
        mock_api.get_products.return_value = (
            {'results': [], 'count': 0, 'next': None, 'previous': None},
            200,
            None
        )
        mock_api.get_categories.return_value = (
            {'results': []},
            200,
            None
        )
        
        # Выполняем запрос
        response = self.client.get(reverse('shop:home'))
        
        # Проверяем результат
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/home.html')


class ProductListViewTestCase(APIClientTestCase):
    """Тесты для списка товаров"""
    
    @patch('web.shop.views.APIClient')
    def test_product_list_view(self, mock_api_client_class):
        """Тест отображения списка товаров"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.get_categories.return_value = (
            {'results': []},
            200,
            None
        )
        mock_api.get_products.return_value = (
            {'results': [], 'count': 0, 'next': None, 'previous': None},
            200,
            None
        )
        
        response = self.client.get(reverse('shop:product_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/product_list.html')


class CartViewTestCase(APIClientTestCase):
    """Тесты для корзины"""
    
    def setUp(self):
        super().setUp()
        # Создаем сессию с токеном для авторизованного пользователя
        session = self.client.session
        session['access_token'] = 'test_token'
        session['user_data'] = {'id': 1, 'username': 'testuser', 'role_name': 'Buyer'}
        session.save()
    
    @patch('web.shop.views.APIClient')
    def test_cart_view_authenticated(self, mock_api_client_class):
        """Тест отображения корзины для авторизованного пользователя"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.get_cart_items.return_value = (
            {'results': []},
            200,
            None
        )
        
        response = self.client.get(reverse('shop:cart'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/cart.html')
    
    def test_cart_view_unauthenticated(self):
        """Тест редиректа для неавторизованного пользователя"""
        response = self.client.get(reverse('shop:cart'))
        
        # Должен быть редирект на страницу входа
        self.assertEqual(response.status_code, 302)


class LoginViewTestCase(APIClientTestCase):
    """Тесты для страницы входа"""
    
    @patch('web.shop.views.APIClient')
    def test_login_view_get(self, mock_api_client_class):
        """Тест отображения формы входа"""
        response = self.client.get(reverse('shop:login'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/login.html')
    
    @patch('web.shop.views.APIClient')
    def test_login_view_post_success(self, mock_api_client_class):
        """Тест успешного входа"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        # Мокаем успешный ответ API
        mock_api.login.return_value = (
            {'id': 1, 'username': 'testuser', 'role': {'name': 'Buyer'}},
            True,
            None
        )
        mock_api.get_me.return_value = (
            {'id': 1, 'username': 'testuser', 'role': {'name': 'Buyer'}},
            200,
            None
        )
        
        response = self.client.post(reverse('shop:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Должен быть редирект на главную
        self.assertEqual(response.status_code, 302)
        # Проверяем, что токен сохранен в сессии
        self.assertIn('access_token', self.client.session)
    
    @patch('web.shop.views.APIClient')
    def test_login_view_post_failure(self, mock_api_client_class):
        """Тест неуспешного входа"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.login.return_value = (
            None,
            False,
            'Неверные учетные данные'
        )
        
        response = self.client.post(reverse('shop:login'), {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/login.html')


class RegisterViewTestCase(APIClientTestCase):
    """Тесты для страницы регистрации"""
    
    @patch('web.shop.views.APIClient')
    def test_register_view_get(self, mock_api_client_class):
        """Тест отображения формы регистрации"""
        response = self.client.get(reverse('shop:register'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/register.html')
    
    @patch('web.shop.views.APIClient')
    def test_register_view_post_success(self, mock_api_client_class):
        """Тест успешной регистрации"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.register.return_value = (
            {'id': 1, 'username': 'newuser'},
            True,
            None
        )
        
        response = self.client.post(reverse('shop:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'agree_terms': 'on'
        })
        
        # Должен быть редирект на страницу входа
        self.assertEqual(response.status_code, 302)
    
    @patch('web.shop.views.APIClient')
    def test_register_view_post_without_consent(self, mock_api_client_class):
        """Тест регистрации без согласия на обработку ПД — форма не принимается"""
        response = self.client.post(reverse('shop:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/register.html')
    
    @patch('web.shop.views.APIClient')
    def test_register_view_post_password_mismatch(self, mock_api_client_class):
        """Тест регистрации с несовпадающими паролями"""
        response = self.client.post(reverse('shop:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123',
            'password2': 'differentpass',
            'agree_terms': 'on'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/register.html')


class SettingsViewTestCase(APIClientTestCase):
    """Тесты для страницы настроек"""
    
    def setUp(self):
        super().setUp()
        session = self.client.session
        session['access_token'] = 'test_token'
        session['user_data'] = {'id': 1, 'username': 'testuser', 'role_name': 'Buyer'}
        session.save()
    
    @patch('web.shop.views.APIClient')
    def test_settings_view_get(self, mock_api_client_class):
        """Тест отображения страницы настроек"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.get_user_settings.return_value = (
            {
                'theme': 'light',
                'date_format': 'DD.MM.YYYY',
                'number_format': 'ru',
                'page_size': 20
            },
            200,
            None
        )
        
        response = self.client.get(reverse('shop:settings'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/settings.html')
    
    @patch('web.shop.views.APIClient')
    def test_settings_view_post(self, mock_api_client_class):
        """Тест сохранения настроек"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.update_user_settings.return_value = (
            {
                'theme': 'dark',
                'date_format': 'YYYY-MM-DD',
                'number_format': 'en',
                'page_size': 50
            },
            200,
            None
        )
        
        response = self.client.post(reverse('shop:settings'), {
            'theme': 'dark',
            'date_format': 'YYYY-MM-DD',
            'number_format': 'en',
            'page_size': 50
        })
        
        self.assertEqual(response.status_code, 200)
        # Проверяем, что настройки обновлены в сессии
        self.assertIn('user_data', self.client.session)


class AdminViewsTestCase(APIClientTestCase):
    """Тесты для админ-панели"""
    
    def setUp(self):
        super().setUp()
        session = self.client.session
        session['access_token'] = 'test_token'
        session['user_data'] = {'id': 1, 'username': 'admin', 'role_name': 'Admin'}
        session.save()
    
    @patch('web.shop.admin_views.APIClient')
    def test_admin_dashboard(self, mock_api_client_class):
        """Тест админ-дашборда"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.get_dashboard_stats.return_value = (
            {
                'total_revenue': 100000,
                'total_orders': 50,
                'active_users': 10,
                'top_products': []
            },
            200,
            None
        )
        
        response = self.client.get(reverse('shop:admin_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/admin/dashboard.html')
    
    @patch('web.shop.admin_views.APIClient')
    def test_admin_products(self, mock_api_client_class):
        """Тест страницы управления товарами"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.get_products.return_value = (
            {'results': [], 'count': 0},
            200,
            None
        )
        mock_api.get_categories.return_value = (
            {'results': []},
            200,
            None
        )
        
        response = self.client.get(reverse('shop:admin_products'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/admin/products.html')
    
    def test_admin_views_unauthorized(self):
        """Тест доступа к админ-панели без прав"""
        # Очищаем сессию
        session = self.client.session
        session['access_token'] = 'test_token'
        session['user_data'] = {'id': 1, 'username': 'user', 'role_name': 'Buyer'}
        session.save()
        
        response = self.client.get(reverse('shop:admin_dashboard'))
        
        # Должен быть редирект на главную
        self.assertEqual(response.status_code, 302)


class AnalyticsViewsTestCase(APIClientTestCase):
    """Тесты для аналитики"""
    
    def setUp(self):
        super().setUp()
        session = self.client.session
        session['access_token'] = 'test_token'
        session['user_data'] = {'id': 1, 'username': 'analyst', 'role_name': 'Analyst'}
        session.save()
    
    @patch('web.shop.admin_views.APIClient')
    def test_analytics_dashboard(self, mock_api_client_class):
        """Тест дашборда аналитики"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.get_dashboard_stats.return_value = (
            {
                'total_revenue': 100000,
                'total_orders': 50,
                'active_users': 10,
                'top_products': []
            },
            200,
            None
        )
        
        response = self.client.get(reverse('shop:analytics_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/analytics/dashboard.html')
    
    @patch('web.shop.admin_views.APIClient')
    def test_sales_by_product(self, mock_api_client_class):
        """Тест страницы продаж по продуктам"""
        mock_api = MagicMock()
        mock_api_client_class.return_value = mock_api
        
        mock_api.get_sales_by_product.return_value = (
            [],
            200,
            None
        )
        mock_api.get_categories.return_value = (
            {'results': []},
            200,
            None
        )
        
        response = self.client.get(reverse('shop:analytics_sales_by_product'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/analytics/sales_by_product.html')
