"""
API клиент для взаимодействия с основным API
"""
import requests
from django.conf import settings
import json
from urllib.parse import urljoin, urlparse

class APIClient:
    """Клиент для работы с API"""
    
    BASE_URL = getattr(settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1')
    
    def __init__(self, session=None):
        """
        Инициализация клиента
        
        Args:
            session: Django session объект для хранения токенов
        """
        self.session = session
        self.access_token = None
        if session:
            self.access_token = session.get('access_token')
            self.refresh_token = session.get('refresh_token')
    
    def _get_headers(self, require_auth=False):
        """
        Получить заголовки для запроса
        
        Args:
            require_auth: Если True, токен обязателен. Если False, токен добавляется только если он есть.
        """
        headers = {
            'Content-Type': 'application/json',
        }
        # Обновляем токен из сессии, если он был изменен
        if self.session:
            session_token = self.session.get('access_token')
            if session_token and session_token != self.access_token:
                self.access_token = session_token
        
        # Если требуется аутентификация, проверяем наличие токена
        if require_auth:
            if not self.access_token:
                raise ValueError('Требуется аутентификация, но токен отсутствует')
            headers['Authorization'] = f'Bearer {self.access_token}'
        elif self.access_token:
            # Для публичных эндпоинтов добавляем токен, если он есть
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        return headers
    
    def _make_request(self, method, endpoint, data=None, params=None, require_auth=False):
        """
        Выполнить HTTP запрос к API
        
        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: endpoint API (без BASE_URL)
            data: данные для отправки (будет преобразовано в JSON)
            params: query параметры
            require_auth: Требуется ли аутентификация для этого запроса
        
        Returns:
            tuple: (response_data, status_code, error_message)
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers(require_auth=require_auth)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return None, 405, f'Неподдерживаемый метод: {method}'
            
            # Попытка распарсить JSON ответ
            try:
                response_data = response.json()
            except:
                response_data = {'detail': response.text} if response.text else {}
            
            # Если получили 401 и это публичный эндпоинт, пробуем без токена
            if response.status_code == 401 and not require_auth and self.access_token:
                # Удаляем токен из заголовков и повторяем запрос
                headers_without_token = {k: v for k, v in headers.items() if k != 'Authorization'}
                try:
                    if method == 'GET':
                        retry_response = requests.get(url, headers=headers_without_token, params=params, timeout=10)
                    elif method == 'POST':
                        retry_response = requests.post(url, headers=headers_without_token, json=data, timeout=10)
                    elif method == 'PUT':
                        retry_response = requests.put(url, headers=headers_without_token, json=data, timeout=10)
                    elif method == 'DELETE':
                        retry_response = requests.delete(url, headers=headers_without_token, timeout=10)
                    else:
                        retry_response = None
                    
                    if retry_response and retry_response.status_code != 401:
                        # Успешно получили ответ без токена
                        try:
                            response_data = retry_response.json()
                        except:
                            response_data = {'detail': retry_response.text} if retry_response.text else {}
                        response = retry_response
                except:
                    pass  # Если повторный запрос не удался, используем оригинальный ответ
            
            # Сохраняем токены при успешной аутентификации
            # Проверяем разные форматы ответа с токенами
            tokens = None
            if 'access' in response_data and 'refresh' in response_data:
                # Формат: {"access": "...", "refresh": "..."}
                tokens = {
                    'access': response_data['access'],
                    'refresh': response_data['refresh']
                }
            elif 'tokens' in response_data and isinstance(response_data['tokens'], dict):
                # Формат: {"tokens": {"access": "...", "refresh": "..."}}
                tokens = response_data['tokens']
            
            if tokens:
                self.access_token = tokens.get('access')
                self.refresh_token = tokens.get('refresh')
                if self.session:
                    self.session['access_token'] = self.access_token
                    self.session['refresh_token'] = self.refresh_token
                    self.session.save()
            
            # Обработка ошибок HTTP
            if response.status_code >= 400:
                # Если получили 401 и требуется аутентификация, пытаемся обновить токен
                # Обновляем refresh_token из сессии, если он не установлен
                if not self.refresh_token and self.session:
                    self.refresh_token = self.session.get('refresh_token')
                
                if response.status_code == 401 and require_auth and self.refresh_token:
                    # Пытаемся обновить токен
                    refresh_success = self._refresh_access_token()
                    if refresh_success:
                        # Повторяем запрос с новым токеном
                        headers = self._get_headers(require_auth=require_auth)
                        try:
                            if method == 'GET':
                                response = requests.get(url, headers=headers, params=params, timeout=10)
                            elif method == 'POST':
                                response = requests.post(url, headers=headers, json=data, timeout=10)
                            elif method == 'PUT':
                                response = requests.put(url, headers=headers, json=data, timeout=10)
                            elif method == 'DELETE':
                                response = requests.delete(url, headers=headers, timeout=10)
                            
                            # Парсим ответ повторного запроса
                            try:
                                response_data = response.json()
                            except:
                                response_data = {'detail': response.text} if response.text else {}
                            
                            # Если успешно, возвращаем результат
                            if response.status_code < 400:
                                return response_data, response.status_code, None
                        except:
                            pass  # Если повторный запрос не удался, продолжаем с оригинальной ошибкой
                
                # Формируем понятное сообщение об ошибке
                error_msg = None
                if isinstance(response_data, dict):
                    if 'detail' in response_data:
                        error_msg = response_data['detail']
                    elif 'error' in response_data:
                        error_msg = response_data['error']
                    elif 'non_field_errors' in response_data:
                        error_msg = '; '.join(response_data['non_field_errors'])
                    else:
                        # Собираем все ошибки валидации
                        errors = []
                        for key, value in response_data.items():
                            if isinstance(value, list):
                                errors.extend([f"{key}: {v}" for v in value])
                            else:
                                errors.append(f"{key}: {value}")
                        if errors:
                            error_msg = '; '.join(errors)
                
                return response_data, response.status_code, error_msg or f'Ошибка {response.status_code}'
            
            return response_data, response.status_code, None
            
        except ValueError as e:
            # Ошибка аутентификации
            return None, 401, str(e)
        except requests.exceptions.RequestException as e:
            return None, 0, f'Ошибка подключения к API: {str(e)}'
    
    def _refresh_access_token(self):
        """
        Обновить access token используя refresh token
        
        Returns:
            bool: True если токен успешно обновлен, False в противном случае
        """
        if not self.refresh_token:
            # Обновляем refresh_token из сессии
            if self.session:
                self.refresh_token = self.session.get('refresh_token')
            if not self.refresh_token:
                return False
        
        try:
            url = f"{self.BASE_URL}/auth/refresh/"
            headers = {'Content-Type': 'application/json'}
            data = {'refresh': self.refresh_token}
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Обновляем токены
                if 'access' in response_data:
                    self.access_token = response_data['access']
                    if 'refresh' in response_data:
                        self.refresh_token = response_data['refresh']
                    
                    # Сохраняем в сессию
                    if self.session:
                        self.session['access_token'] = self.access_token
                        if 'refresh' in response_data:
                            self.session['refresh_token'] = self.refresh_token
                        self.session.save()
                    
                    return True
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            pass
        
        return False

    def _get_api_origin(self):
        """Получить origin API (например, http://127.0.0.1:8000)."""
        parsed = urlparse(self.BASE_URL)
        if parsed.scheme and parsed.netloc:
            return f'{parsed.scheme}://{parsed.netloc}/'
        return self.BASE_URL.rstrip('/') + '/'

    def _normalize_image_url(self, image_url):
        """Нормализовать URL изображения: поддержка относительных путей и альтернативных полей."""
        if image_url is None:
            return None
        if not isinstance(image_url, str):
            image_url = str(image_url)

        image_url = image_url.strip()
        if not image_url:
            return None

        # Полный URL оставляем без изменений
        if image_url.startswith('http://') or image_url.startswith('https://'):
            return image_url

        # Схема-less URL (//cdn...) приводим к https
        if image_url.startswith('//'):
            return f'https:{image_url}'

        # Относительный путь привязываем к origin API
        return urljoin(self._get_api_origin(), image_url.lstrip('/'))

    def _normalize_product_image(self, product):
        """Привести поле изображения товара к image_url для единообразного рендера."""
        if not isinstance(product, dict):
            return product

        image_value = (
            product.get('image_url')
            or product.get('image')
            or product.get('imageUrl')
            or product.get('image_path')
        )
        product['image_url'] = self._normalize_image_url(image_value)
        return product
    
    def login(self, username, password):
        """
        Вход пользователя
        
        Args:
            username: имя пользователя
            password: пароль
        
        Returns:
            tuple: (user_data, success, error_message)
        """
        data = {'username': username, 'password': password}
        response_data, status_code, error = self._make_request('POST', '/auth/login/', data=data)
        
        if status_code == 200:
            # Токены уже сохранены в _make_request, теперь получаем информацию о пользователе
            # Используем данные из ответа или запрашиваем /auth/me/
            if 'user' in response_data:
                # Если в ответе уже есть данные пользователя, используем их
                user_data = response_data['user']
            else:
                # Иначе запрашиваем через /auth/me/
                user_data, user_status, user_error = self._make_request('GET', '/auth/me/')
                if user_status != 200:
                    # Если не удалось получить данные, используем базовую информацию
                    user_data = response_data.get('user', {})
            
            return user_data, True, None
        elif error:
            return None, False, error
        else:
            error_msg = response_data.get('error') or response_data.get('detail', 'Ошибка входа')
            if 'non_field_errors' in response_data:
                error_msg = response_data['non_field_errors'][0]
            return None, False, error_msg
    
    def register(self, username, email, password):
        """
        Регистрация пользователя
        
        Args:
            username: имя пользователя
            email: email
            password: пароль
        
        Returns:
            tuple: (user_data, success, error_message)
        """
        data = {
            'username': username,
            'email': email,
            'password': password
        }
        response_data, status_code, error = self._make_request('POST', '/auth/register/', data=data)

        if status_code == 201:
            return response_data, True, None
        elif error:
            return None, False, error
        else:
            error_msg = 'Ошибка регистрации'
            if 'detail' in response_data:
                error_msg = response_data['detail']
            elif isinstance(response_data, dict):
                # Собираем все ошибки валидации
                errors = []
                for field, messages in response_data.items():
                    if isinstance(messages, list):
                        errors.extend([f"{field}: {msg}" for msg in messages])
                    else:
                        errors.append(f"{field}: {messages}")
                if errors:
                    error_msg = '; '.join(errors)
            return None, False, error_msg
    
    def get_me(self):
        """Получить информацию о текущем пользователе"""
        return self._make_request('GET', '/auth/me/')
    
    def password_reset_request(self, email):
        """Запрос на сброс пароля. На email отправляется ссылка."""
        data = {'email': email}
        return self._make_request('POST', '/auth/password-reset/', data=data)
    
    def password_reset_confirm(self, token, new_password):
        """Установка нового пароля по токену из письма."""
        data = {'token': token, 'new_password': new_password}
        return self._make_request('POST', '/auth/password-reset-confirm/', data=data)
    
    def get_categories(self, parent=None):
        """Получить список категорий"""
        params = {}
        if parent is not None:
            params['parent'] = parent
        return self._make_request('GET', '/categories/', params=params)
    
    def get_products(self, category_id=None, search=None, page=1, page_size=12, available_only=None, sort=None):
        """Получить список товаров
        
        Args:
            category_id: ID категории для фильтрации
            search: поисковый запрос
            page: номер страницы
            page_size: размер страницы
            available_only: фильтр по доступности (True - только доступные, False - все, None - по умолчанию True)
            sort: сортировка с веб-формы: created_at, price_asc, price_desc, name
        """
        params = {
            'page': page,
            'page_size': page_size
        }
        if category_id:
            params['category'] = category_id
        if search:
            params['search'] = search
        if available_only is not None:
            params['available_only'] = 'true' if available_only else 'false'
        # Преобразуем значение сортировки из веб-формы в параметр ordering API
        ordering_map = {
            'created_at': '-created_at',
            'price_asc': 'price',
            'price_desc': '-price',
            'name': 'name',
        }
        ordering = ordering_map.get(sort, '-created_at') if sort else '-created_at'
        params['ordering'] = ordering
        response_data, status_code, error = self._make_request('GET', '/products/', params=params)

        # Нормализуем image_url в списке товаров для корректного отображения в шаблонах.
        if status_code == 200 and isinstance(response_data, dict) and isinstance(response_data.get('results'), list):
            response_data['results'] = [self._normalize_product_image(product) for product in response_data['results']]

        return response_data, status_code, error
    
    def get_product(self, product_id):
        """Получить детали товара"""
        response_data, status_code, error = self._make_request('GET', f'/products/{product_id}/')

        if status_code == 200 and isinstance(response_data, dict):
            response_data = self._normalize_product_image(response_data)

        return response_data, status_code, error
    
    def get_cart(self):
        """Получить корзину"""
        return self._make_request('GET', '/cart/')
    
    def get_cart_items(self):
        """Получить элементы корзины"""
        return self._make_request('GET', '/cart/items/')
    
    def add_to_cart(self, product_id, quantity=1):
        """Добавить товар в корзину"""
        data = {
            'product_id': product_id,
            'quantity': quantity
        }
        return self._make_request('POST', '/cart/items/', data=data)
    
    def update_cart_item(self, item_id, quantity):
        """Обновить количество товара в корзине"""
        data = {'quantity': quantity}
        return self._make_request('PUT', f'/cart/items/{item_id}/', data=data)
    
    def remove_from_cart(self, item_id):
        """Удалить товар из корзины"""
        return self._make_request('DELETE', f'/cart/items/{item_id}/')
    
    # Admin methods for managing user carts
    def get_user_cart(self, user_id):
        """Получить корзину пользователя (для админа)"""
        return self._make_request('GET', f'/cart/admin/users/{user_id}/', require_auth=True)
    
    def add_to_user_cart(self, user_id, product_id, quantity=1):
        """Добавить товар в корзину пользователя (для админа)"""
        data = {
            'product_id': product_id,
            'quantity': quantity
        }
        return self._make_request('POST', f'/cart/admin/users/{user_id}/items/', data=data, require_auth=True)
    
    def update_user_cart_item(self, user_id, item_id, quantity):
        """Обновить элемент корзины пользователя (для админа)"""
        data = {'quantity': quantity}
        return self._make_request('PUT', f'/cart/admin/users/{user_id}/items/{item_id}/', data=data, require_auth=True)
    
    def delete_user_cart_item(self, user_id, item_id):
        """Удалить элемент корзины пользователя (для админа)"""
        return self._make_request('DELETE', f'/cart/admin/users/{user_id}/items/{item_id}/delete/', require_auth=True)
    
    def clear_user_cart(self, user_id):
        """Очистить корзину пользователя (для админа)"""
        return self._make_request('DELETE', f'/cart/admin/users/{user_id}/clear/', require_auth=True)
    
    def get_orders(self):
        """Получить список заказов"""
        return self._make_request('GET', '/orders/')
    
    def get_order(self, order_id):
        """Получить детали заказа"""
        return self._make_request('GET', f'/orders/{order_id}/')
    
    def get_order_transactions(self, order_id):
        """Получить транзакции заказа"""
        return self._make_request('GET', f'/orders/{order_id}/transactions/')
    
    def get_all_transactions(self, order_id=None, status=None, page=1):
        """Получить все транзакции (для админа)"""
        params = {'page': page}
        if order_id:
            params['order'] = order_id
        if status:
            params['status'] = status
        # Получаем транзакции через заказы, так как отдельного endpoint может не быть
        # Используем список заказов и собираем транзакции
        return self._make_request('GET', '/orders/', params=params, require_auth=True)
    
    def update_order(self, order_id, order_data):
        """Обновить заказ"""
        return self._make_request('PUT', f'/orders/{order_id}/', data=order_data, require_auth=True)
    
    def delete_order(self, order_id):
        """Удалить заказ"""
        return self._make_request('DELETE', f'/orders/{order_id}/', require_auth=True)
    
    def create_order(self):
        """Создать заказ из корзины"""
        return self._make_request('POST', '/orders/create/', data={})
    
    def create_payment(self, order_id, amount, payment_method, card_number=None, card_expiry=None, card_cvv=None, cardholder_name=None, save_card=False, use_saved_card=None, delivery_address=None):
        """Создать платеж для заказа"""
        data = {
            'amount': str(amount),
            'payment_method': payment_method
        }
        if use_saved_card:
            # Используем сохраненную карту
            data['use_saved_card'] = use_saved_card
        else:
            # Используем новую карту
            if card_number:
                data['card_number'] = card_number
            if card_expiry:
                data['card_expiry'] = card_expiry
            if card_cvv:
                data['card_cvv'] = card_cvv
            if cardholder_name:
                data['cardholder_name'] = cardholder_name
            if save_card:
                data['save_card'] = save_card
        
        # Добавляем адрес доставки
        if delivery_address:
            data['delivery_address'] = delivery_address
        
        return self._make_request('POST', f'/orders/{order_id}/pay/', data=data)
    
    def get_saved_cards(self):
        """Получить сохраненные карты пользователя"""
        me_data, status, error = self.get_me()
        if status == 200 and me_data:
            return me_data.get('saved_cards', [])
        return []
    
    # Analytics methods
    def get_dashboard_stats(self):
        """Получить статистику дашборда"""
        return self._make_request('GET', '/analytics/dashboard/')
    
    def get_sales_by_product(self, category_id=None, date_from=None, date_to=None):
        """Получить продажи по продуктам"""
        params = {}
        if category_id:
            params['category'] = category_id
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to
        return self._make_request('GET', '/analytics/sales-by-product/', params=params)
    
    def get_monthly_sales(self, year=None):
        """Получить ежемесячные продажи"""
        params = {}
        if year:
            params['year'] = year
        return self._make_request('GET', '/analytics/monthly-sales/', params=params)
    
    def get_top_products(self, limit=10):
        """Получить топ товаров"""
        params = {'limit': limit}
        return self._make_request('GET', '/analytics/top-products/', params=params)
    
    def get_revenue(self, date_from, date_to):
        """Получить выручку за период"""
        params = {
            'date_from': date_from,
            'date_to': date_to
        }
        return self._make_request('GET', '/analytics/revenue/', params=params)
    
    # Admin methods
    def create_category(self, name, description=None, parent_id=None):
        """Создать категорию"""
        data = {'name': name}
        if description:
            data['description'] = description
        if parent_id:
            data['parent'] = parent_id
        return self._make_request('POST', '/categories/', data=data)
    
    def update_category(self, category_id, name=None, description=None, parent_id=None):
        """Обновить категорию"""
        data = {}
        if name:
            data['name'] = name
        if description:
            data['description'] = description
        if parent_id:
            data['parent'] = parent_id
        return self._make_request('PUT', f'/categories/{category_id}/', data=data)
    
    def delete_category(self, category_id):
        """Удалить категорию"""
        return self._make_request('DELETE', f'/categories/{category_id}/')
    
    def create_product(self, product_data):
        """Создать товар"""
        return self._make_request('POST', '/products/', data=product_data)
    
    def update_product(self, product_id, product_data):
        """Обновить товар"""
        return self._make_request('PUT', f'/products/{product_id}/', data=product_data)
    
    def delete_product(self, product_id):
        """Удалить товар"""
        return self._make_request('DELETE', f'/products/{product_id}/')
    
    def get_roles(self):
        """Получить список ролей"""
        return self._make_request('GET', '/roles/')
    
    def get_users(self, search=None):
        """Получить список пользователей. search — поиск по имени и email."""
        params = {}
        if search and str(search).strip():
            params['search'] = str(search).strip()
        return self._make_request(
            'GET', '/users/',
            params=params if params else None,
            require_auth=True
        )
    
    def get_user(self, user_id):
        """Получить пользователя"""
        return self._make_request('GET', f'/users/{user_id}/')
    
    def create_user(self, user_data):
        """Создать пользователя"""
        return self._make_request('POST', '/users/', data=user_data, require_auth=True)
    
    def update_user(self, user_id, user_data):
        """Обновить пользователя"""
        return self._make_request('PUT', f'/users/{user_id}/', data=user_data, require_auth=True)
    
    def delete_user(self, user_id):
        """Удалить пользователя"""
        return self._make_request('DELETE', f'/users/{user_id}/', require_auth=True)
    
    def get_user_settings(self):
        """Получить настройки текущего пользователя"""
        return self._make_request('GET', '/users/me/settings/', require_auth=True)
    
    def update_user_settings(self, settings):
        """Обновить настройки текущего пользователя"""
        return self._make_request('PUT', '/users/me/settings/', data=settings, require_auth=True)
    
    # Admin methods (logs, audit, backups)
    def get_logs(self, level=None, user_id=None, date_from=None, date_to=None, page=1, page_size=None):
        """Получить список логов"""
        params = {'page': page}
        if page_size is not None:
            params['page_size'] = page_size
        if level:
            params['level'] = level
        if user_id:
            params['user'] = user_id
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to
        return self._make_request('GET', '/admin/logs/', params=params)
    
    def get_audit_logs(self, action=None, table_name=None, user_id=None, date_from=None, date_to=None, page=1):
        """Получить список записей аудита"""
        params = {'page': page}
        if action:
            params['action'] = action
        if table_name:
            params['table_name'] = table_name
        if user_id:
            params['user'] = user_id
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to
        return self._make_request('GET', '/admin/audit/', params=params)
    
    def get_backups(self):
        """Получить список резервных копий"""
        return self._make_request('GET', '/admin/backups/')
    
    def create_backup(self, description=None):
        """Создать резервную копию"""
        data = {}
        if description:
            data['description'] = description
        return self._make_request('POST', '/admin/backups/create/', data=data)
    
    def download_backup(self, backup_id):
        """Скачать резервную копию"""
        return self._make_request('GET', f'/admin/backups/{backup_id}/download/', require_auth=True)
    
    def restore_backup(self, backup_id):
        """Восстановить из резервной копии"""
        return self._make_request('POST', f'/admin/backups/{backup_id}/restore/')
    
    def get_backup_schedule(self):
        """Получить расписание автоматических бекапов"""
        return self._make_request('GET', '/admin/backups/schedule/', require_auth=True)
    
    def update_backup_schedule(self, schedule_data):
        """Обновить расписание автоматических бекапов"""
        return self._make_request('PUT', '/admin/backups/schedule/', data=schedule_data, require_auth=True)

