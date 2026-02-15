"""
Тесты аутентификации, управления пользователями и сброса пароля.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Role
from .services import UserService

User = get_user_model()


class AuthenticationTestCase(TestCase):
    """Тесты для аутентификации"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.client = APIClient()
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
    
    def test_register_user(self):
        """Тест регистрации пользователя"""
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
        response = self.client.post('/api/v1/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user_id', response.data)
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_register_user_duplicate_username(self):
        """Тест регистрации с дублирующимся именем пользователя"""
        User.objects.create_user(
            username='existing',
            email='existing@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        
        data = {
            'username': 'existing',
            'email': 'new@test.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        }
        response = self.client.post('/api/v1/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_success(self):
        """Тест успешного входа"""
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post('/api/v1/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data.get('tokens', {}))
        self.assertIn('refresh', response.data.get('tokens', {}))
    
    def test_login_invalid_credentials(self):
        """Тест входа с неверными учетными данными"""
        User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post('/api/v1/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_current_user(self):
        """Тест получения информации о текущем пользователе"""
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        
        response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')


class UserManagementTestCase(TestCase):
    """Тесты для управления пользователями"""
    
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
    
    def get_admin_token(self):
        """Получить токен администратора"""
        refresh = RefreshToken.for_user(self.admin)
        return str(refresh.access_token)
    
    def get_buyer_token(self):
        """Получить токен покупателя"""
        refresh = RefreshToken.for_user(self.buyer)
        return str(refresh.access_token)
    
    def test_list_users_admin(self):
        """Тест получения списка пользователей администратором"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_list_users_buyer_forbidden(self):
        """Тест запрета получения списка пользователей покупателем"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_get_user_detail_admin(self):
        """Тест получения деталей пользователя администратором"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_admin_token()}')
        response = self.client.get(f'/api/v1/users/{self.buyer.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'buyer')
    
    def test_update_user_settings(self):
        """Тест обновления настроек пользователя"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.get_buyer_token()}')
        data = {
            'theme': 'dark',
            'date_format': 'YYYY-MM-DD',
            'page_size': 50
        }
        response = self.client.put('/api/v1/users/me/settings/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['theme'], 'dark')


class UserServiceTestCase(TestCase):
    """Тесты для сервиса пользователей"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.admin_role, _ = Role.objects.get_or_create(name='Admin')
    
    def test_register_user_service(self):
        """Тест регистрации пользователя через сервис"""
        user_id = UserService.register_user(
            username='serviceuser',
            email='service@test.com',
            password='testpass123',
            role_name='Buyer'
        )
        
        self.assertIsNotNone(user_id)
        user = User.objects.get(id=user_id)
        self.assertEqual(user.username, 'serviceuser')
        self.assertEqual(user.role.name, 'Buyer')
    
    def test_register_user_duplicate(self):
        """Тест регистрации с дублирующимся именем"""
        UserService.register_user(
            username='duplicate',
            email='dup1@test.com',
            password='testpass123',
            role_name='Buyer'
        )
        
        with self.assertRaises(ValueError):
            UserService.register_user(
                username='duplicate',
                email='dup2@test.com',
                password='testpass123',
                role_name='Buyer'
            )


class FiveUnitTests(TestCase):
    """
    5 unit-тестов для прогона.
    Запуск: python manage.py test apps.accounts.tests.FiveUnitTests
    """

    def setUp(self):
        self.client = APIClient()
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')

    def test_1_password_reset_request_empty_email_returns_400(self):
        """Запрос сброса пароля без email возвращает 400."""
        response = self.client.post(
            '/api/v1/auth/password-reset/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_2_password_reset_request_with_email_returns_200(self):
        """Запрос сброса пароля с email возвращает 200 (даже для неизвестного email)."""
        response = self.client.post(
            '/api/v1/auth/password-reset/',
            {'email': 'unknown@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

    def test_3_password_reset_confirm_without_token_returns_400(self):
        """Подтверждение сброса пароля без токена возвращает 400."""
        response = self.client.post(
            '/api/v1/auth/password-reset-confirm/',
            {'new_password': 'newvalidpass123'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_4_password_reset_confirm_short_password_returns_400(self):
        """Подтверждение сброса с коротким паролем (< 8 символов) возвращает 400."""
        response = self.client.post(
            '/api/v1/auth/password-reset-confirm/',
            {'token': 'sometoken', 'new_password': 'short'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_5_registration_confirmation_email_service_calls_send_mail(self):
        """Сервис отправки письма подтверждения регистрации вызывает send_mail с нужными аргументами."""
        from unittest.mock import patch
        from .email_service import send_registration_confirmation
        with patch('apps.accounts.email_service.send_mail') as mock_send_mail:
            send_registration_confirmation('user@test.com', 'testuser')
            mock_send_mail.assert_called_once()
            call_kw = mock_send_mail.call_args[1]
            self.assertIn('user@test.com', call_kw['recipient_list'])
            self.assertIn('testuser', call_kw['message'])
            self.assertEqual(call_kw['subject'], 'Подтверждение регистрации — СпортМаг')

