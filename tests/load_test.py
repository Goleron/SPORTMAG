"""
Скрипт для нагрузочного тестирования с использованием Locust
"""
from locust import HttpUser, task, between
import random
import string


class ShopUser(HttpUser):
    """Пользователь для нагрузочного тестирования"""
    wait_time = between(1, 3)  # Ожидание между запросами 1-3 секунды
    
    def on_start(self):
        """Выполняется при старте пользователя"""
        # Регистрируем пользователя
        username = ''.join(random.choices(string.ascii_lowercase, k=8))
        email = f'{username}@test.com'
        password = 'testpass123'
        
        register_data = {
            'username': username,
            'email': email,
            'password': password,
            'password_confirm': password
        }
        
        response = self.client.post('/api/v1/auth/register/', json=register_data)
        if response.status_code == 201:
            self.tokens = response.json().get('tokens', {})
            self.access_token = self.tokens.get('access')
            self.headers = {'Authorization': f'Bearer {self.access_token}'}
        else:
            # Если регистрация не удалась, пробуем войти
            login_data = {
                'username': username,
                'password': password
            }
            response = self.client.post('/api/v1/auth/login/', json=login_data)
            if response.status_code == 200:
                self.tokens = response.json().get('tokens', {})
                self.access_token = self.tokens.get('access')
                self.headers = {'Authorization': f'Bearer {self.access_token}'}
    
    @task(3)
    def view_products(self):
        """Просмотр товаров (высокая частота)"""
        self.client.get('/api/v1/products/', headers=self.headers if hasattr(self, 'headers') else None)
    
    @task(2)
    def view_categories(self):
        """Просмотр категорий"""
        self.client.get('/api/v1/categories/', headers=self.headers if hasattr(self, 'headers') else None)
    
    @task(1)
    def view_cart(self):
        """Просмотр корзины"""
        if hasattr(self, 'headers'):
            self.client.get('/api/v1/cart/', headers=self.headers)
    
    @task(1)
    def add_to_cart(self):
        """Добавление товара в корзину"""
        if hasattr(self, 'headers'):
            # Получаем список товаров
            products_response = self.client.get('/api/v1/products/', headers=self.headers)
            if products_response.status_code == 200:
                products = products_response.json().get('results', [])
                if products:
                    product = random.choice(products)
                    data = {
                        'product_id': product['id'],
                        'quantity': random.randint(1, 3)
                    }
                    self.client.post('/api/v1/cart/items/', json=data, headers=self.headers)
    
    @task(1)
    def view_orders(self):
        """Просмотр заказов"""
        if hasattr(self, 'headers'):
            self.client.get('/api/v1/orders/', headers=self.headers)


class AnonymousUser(HttpUser):
    """Анонимный пользователь (только просмотр)"""
    wait_time = between(1, 2)
    
    @task(5)
    def view_products(self):
        """Просмотр товаров"""
        self.client.get('/api/v1/products/')
    
    @task(3)
    def view_categories(self):
        """Просмотр категорий"""
        self.client.get('/api/v1/categories/')
    
    @task(1)
    def view_product_detail(self):
        """Просмотр деталей товара"""
        # Получаем список товаров
        response = self.client.get('/api/v1/products/')
        if response.status_code == 200:
            products = response.json().get('results', [])
            if products:
                product = random.choice(products)
                self.client.get(f"/api/v1/products/{product['id']}/")


# Для запуска: locust -f tests/load_test.py --host=http://127.0.0.1:8000

