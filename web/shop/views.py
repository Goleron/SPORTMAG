"""
Представления для веб-интерфейса магазина (работа через API)
"""
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .api_client import APIClient


def _format_order_date(iso_date):
    """Форматирует дату заказа из ISO-строки (API) в вид дд.мм.гггг чч:мм."""
    if not iso_date:
        return ''
    if hasattr(iso_date, 'strftime'):
        return iso_date.strftime('%d.%m.%Y %H:%M')
    s = str(iso_date).strip()
    if not s:
        return ''
    try:
        s = s.replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        return dt.strftime('%d.%m.%Y %H:%M')
    except (ValueError, TypeError):
        return s[:16] if len(s) >= 16 else s


def get_api_client(request):
    """Получить API клиент с сессией"""
    return APIClient(session=request.session)


def _add_profile_error(request, response_data, error, default_msg):
    """Добавить сообщение об ошибке из ответа API профиля."""
    msg = default_msg
    if error:
        msg = error
    elif response_data and isinstance(response_data, dict):
        if 'detail' in response_data:
            msg = response_data['detail']
        elif 'error' in response_data:
            msg = response_data['error']
        else:
            for key in ('username', 'email', 'password'):
                if key in response_data and isinstance(response_data[key], list):
                    msg = f'{key}: {"; ".join(response_data[key])}'
                    break
    messages.error(request, msg)


def home(request):
    """Главная страница - список популярных товаров"""
    api = get_api_client(request)
    
    # Получаем товары (доступные)
    products_data, status, error = api.get_products(page=1, page_size=12, available_only=True)
    products = products_data.get('results', []) if status == 200 and products_data else []
    
    # Получаем категории
    categories_data, cat_status, cat_error = api.get_categories(parent=None)
    categories = categories_data.get('results', [])[:6] if cat_status == 200 and categories_data else []
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'shop/home.html', context)


def product_list(request, category_slug=None):
    """Список товаров с фильтрацией по категории"""
    api = get_api_client(request)
    
    # Получаем категории для боковой панели
    categories_data, cat_status, cat_error = api.get_categories(parent=None)
    categories = categories_data.get('results', []) if cat_status == 200 else []
    
    # Определяем категорию по slug (с fallback на ID)
    current_category = None
    category_id = None
    if category_slug:
        # Сначала пытаемся найти по slug
        for cat in categories:
            if cat.get('slug') == category_slug:
                current_category = cat
                category_id = cat.get('id')
                break
        
        # Если не нашли по slug, пытаемся найти по ID (на случай если slug не передан правильно)
        if not current_category:
            try:
                # Пробуем интерпретировать category_slug как ID
                potential_id = int(category_slug)
                for cat in categories:
                    if cat.get('id') == potential_id:
                        current_category = cat
                        category_id = cat.get('id')
                        break
            except (ValueError, TypeError):
                pass  # category_slug не является числом
        
        # Если все еще не нашли, пытаемся найти по slug без учета регистра
        if not current_category:
            category_slug_lower = category_slug.lower()
            for cat in categories:
                cat_slug = cat.get('slug', '').lower()
                if cat_slug == category_slug_lower:
                    current_category = cat
                    category_id = cat.get('id')
                    break
    
    # Параметры запроса
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'created_at')
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    
    # Получаем товары (на сайте показываем только доступные товары)
    # ВАЖНО: available_only=True означает, что показываются только товары с is_available=True
    # Если товар не отображается, проверьте:
    # 1. is_available должен быть True
    # 2. category_id должен совпадать с категорией товара
    products_data, status, error = api.get_products(
        category_id=category_id,
        search=search_query if search_query else None,
        page=page,
        page_size=12,
        available_only=True,  # Явно указываем, что нужны только доступные товары
        sort=sort_by
    )
    
    if status == 200:
        products = products_data
        # Отладочная информация (можно убрать в продакшене)
        if current_category and products.get('count', 0) == 0:
            # Сообщение о недоступных товарах только для Admin и Analyst (не для гостей и покупателей)
            user_data = request.session.get('user_data', {})
            user_role = user_data.get('role_name', '')
            if not user_role and isinstance(user_data.get('role'), dict):
                user_role = user_data['role'].get('name', '')
            if user_role in ('Admin', 'Analyst'):
                # Пробуем получить без фильтра available_only для отладки
                debug_products, debug_status, debug_error = api.get_products(
                    category_id=category_id,
                    page=1,
                    page_size=1,
                    available_only=False
                )
                if debug_status == 200 and debug_products.get('count', 0) > 0:
                    messages.info(request, 
                        f'В категории "{current_category.get("name")}" найдено {debug_products.get("count", 0)} товаров, '
                        f'но они не отображаются, так как помечены как недоступные (is_available=False). '
                        f'Проверьте настройки товаров в админ-панели.')
        # Преобразуем API URL пагинации в веб-URL
        from urllib.parse import urlparse, parse_qs
        from urllib.parse import urlencode
        
        # Формируем базовый URL для пагинации
        if category_slug:
            base_url = request.path
        else:
            base_url = request.path
        
        # Извлекаем параметры из next/previous URL и формируем веб-URL
        def convert_pagination_url(api_url):
            if not api_url:
                return None
            try:
                parsed = urlparse(api_url)
                params = parse_qs(parsed.query)
                page_num = params.get('page', [None])[0]
                if page_num:
                    # Формируем веб-URL с параметрами
                    query_params = {}
                    if search_query:
                        query_params['search'] = search_query
                    if sort_by:
                        query_params['sort'] = sort_by
                    query_params['page'] = page_num
                    
                    web_url = base_url + '?' + urlencode(query_params)
                    return web_url
            except Exception as e:
                # В случае ошибки просто возвращаем None
                pass
            return None
        
        # Преобразуем next и previous
        if products.get('next'):
            products['next'] = convert_pagination_url(products['next'])
        if products.get('previous'):
            products['previous'] = convert_pagination_url(products['previous'])
    else:
        products = {'results': [], 'count': 0, 'next': None, 'previous': None}
        if error:
            messages.error(request, f'Ошибка загрузки товаров: {error}')
    
    # Получаем данные пользователя для проверки роли
    user_data = request.session.get('user_data', {})
    
    context = {
        'products': products,
        'categories': categories,
        'current_category': current_category,
        'search_query': search_query,
        'sort_by': sort_by,
        'user_data': user_data,
    }
    return render(request, 'shop/product_list.html', context)


def product_detail(request, product_id):
    """Детальная страница товара"""
    api = get_api_client(request)
    
    # Получаем товар
    product_data, status, error = api.get_product(product_id)
    
    if status != 200:
        messages.error(request, error or 'Товар не найден')
        return redirect('shop:product_list')
    
    product = product_data
    
    # Получаем похожие товары из той же категории
    related_products = []
    if product.get('category'):
        related_data, rel_status, rel_error = api.get_products(
            category_id=product['category'],
            page=1,
            page_size=4
        )
        if rel_status == 200:
            related_products = [p for p in related_data.get('results', []) if p.get('id') != product_id][:4]
    
    # Получаем атрибуты товара (если есть endpoint)
    attributes = product.get('attributes', [])
    
    # Получаем данные пользователя для проверки роли
    user_data = request.session.get('user_data', {})
    
    context = {
        'product': product,
        'attributes': attributes,
        'related_products': related_products,
        'user_data': user_data,
    }
    return render(request, 'shop/product_detail.html', context)


def cart_view(request):
    """Просмотр корзины"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    
    # Получаем элементы корзины
    cart_data, status, error = api.get_cart_items()
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки корзины')
        cart_items = []
        total = 0
    else:
        cart_items = cart_data.get('results', []) if isinstance(cart_data, dict) else cart_data
        # Рассчитываем суммы
        cart_items_with_totals = []
        total = 0
        for item in cart_items:
            product = item.get('product', {})
            quantity = item.get('quantity', 0)
            price = float(product.get('price', 0))
            item_total = price * quantity
            total += item_total
            cart_items_with_totals.append({
                'item': item,
                'total': item_total
            })
        cart_items = cart_items_with_totals
    
    context = {
        'cart_items_with_totals': cart_items,
        'cart_items': cart_items,  # Для обратной совместимости
        'total': total,
    }
    return render(request, 'shop/cart.html', context)


@require_http_methods(["POST"])
def add_to_cart(request, product_id):
    """Добавление товара в корзину"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        messages.error(request, 'Количество должно быть больше нуля')
        return redirect('shop:product_detail', product_id=product_id)
    
    # Добавляем товар в корзину
    response_data, status, error = api.add_to_cart(product_id, quantity)
    
    if status == 201 or status == 200:
        product_name = response_data.get('product', {}).get('name', 'Товар')
        messages.success(request, f'Товар "{product_name}" добавлен в корзину')
    else:
        error_msg = error or response_data.get('detail', 'Ошибка добавления товара')
        if 'non_field_errors' in response_data:
            error_msg = '; '.join(response_data['non_field_errors'])
        messages.error(request, error_msg)
    
    return redirect('shop:cart')


@require_http_methods(["POST"])
def remove_from_cart(request, cart_item_id):
    """Удаление товара из корзины"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    response_data, status, error = api.remove_from_cart(cart_item_id)
    
    if status == 204 or status == 200:
        messages.success(request, 'Товар удален из корзины')
    else:
        messages.error(request, error or 'Ошибка удаления товара')
    
    return redirect('shop:cart')


@require_http_methods(["POST"])
def update_cart(request, cart_item_id):
    """Обновление количества товара в корзине"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        # Удаляем товар, если количество 0
        return remove_from_cart(request, cart_item_id)
    
    response_data, status, error = api.update_cart_item(cart_item_id, quantity)
    
    if status == 200:
        messages.success(request, 'Количество обновлено')
    else:
        error_msg = error or response_data.get('detail', 'Ошибка обновления')
        messages.error(request, error_msg)
    
    return redirect('shop:cart')


def orders_list(request):
    """Список заказов пользователя"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    
    orders_data, status, error = api.get_orders()
    
    if status == 200:
        orders = orders_data.get('results', []) if isinstance(orders_data, dict) else orders_data
        for order in orders:
            if isinstance(order, dict):
                order['order_date_display'] = _format_order_date(
                    order.get('order_date') or order.get('created_at')
                )
    else:
        orders = []
        if error:
            messages.error(request, f'Ошибка загрузки заказов: {error}')
    
    context = {
        'orders': orders,
    }
    return render(request, 'shop/orders.html', context)


@require_http_methods(["GET", "POST"])
def checkout(request):
    """Оформление заказа"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    
    # Получаем корзину
    cart_data, status, error = api.get_cart_items()
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки корзины')
        return redirect('shop:cart')
    
    cart_items = cart_data.get('results', []) if isinstance(cart_data, dict) else cart_data
    
    if not cart_items:
        messages.error(request, 'Корзина пуста')
        return redirect('shop:cart')
    
    # Рассчитываем суммы
    cart_items_with_totals = []
    total = 0
    for item in cart_items:
        product = item.get('product', {})
        quantity = item.get('quantity', 0)
        price = float(product.get('price', 0))
        item_total = price * quantity
        total += item_total
        cart_items_with_totals.append({
            'item': item,
            'total': item_total
        })
    
    if request.method == 'POST':
        # Создаем заказ
        order_data, order_status, order_error = api.create_order()
        
        if order_status == 201:
            order_id = order_data.get('order', {}).get('id') or order_data.get('id')
            messages.success(request, f'Заказ #{order_id} успешно создан!')
            # Перенаправляем на страницу оплаты
            return redirect('shop:payment', order_id=order_id)
        else:
            error_msg = order_error or order_data.get('error', 'Ошибка создания заказа')
            messages.error(request, error_msg)
            return redirect('shop:cart')
    
    context = {
        'cart_items': cart_items,
        'cart_items_with_totals': cart_items_with_totals,
        'total': total,
    }
    return render(request, 'shop/checkout.html', context)


def payment_view(request, order_id):
    """Страница оплаты заказа"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    
    # Получаем информацию о заказе
    order_data, order_status, order_error = api.get_order(order_id)
    
    if order_status != 200:
        messages.error(request, order_error or 'Заказ не найден')
        return redirect('shop:orders')
    
    order = order_data
    total_amount = float(order.get('total_amount', 0))
    
    # Проверяем, можно ли оплатить заказ (разрешаем для Pending и Cancelled)
    can_be_paid = order.get('can_be_paid', False)
    order_status_value = order.get('status', '')
    
    # Если заказ нельзя оплатить через API, но статус позволяет (Pending или Cancelled), разрешаем
    if not can_be_paid and order_status_value not in ['Pending', 'Cancelled']:
        messages.error(request, 'Этот заказ нельзя оплатить')
        return redirect('shop:order_detail', order_id=order_id)
    
    # Получаем сохраненные карты
    saved_cards = api.get_saved_cards()
    
    if request.method == 'POST':
        card_number = request.POST.get('card_number', '').replace(' ', '')
        card_expiry = request.POST.get('card_expiry', '')
        card_cvv = request.POST.get('card_cvv', '')
        cardholder_name = request.POST.get('cardholder_name', '')
        save_card = request.POST.get('save_card') == 'on'
        use_saved_card = request.POST.get('use_saved_card')
        
        # Проверяем адрес доставки (обязателен для всех платежей)
        delivery_address = request.POST.get('delivery_address', '').strip()
        if not delivery_address:
            messages.error(request, 'Необходимо указать адрес доставки')
        elif use_saved_card:
            # Используем сохраненную карту (передаем хеш)
            payment_data, payment_status, payment_error = api.create_payment(
                order_id=order_id,
                amount=total_amount,
                payment_method='Card',
                use_saved_card=use_saved_card,
                delivery_address=delivery_address
            )
        else:
            if not card_number or not card_expiry or not card_cvv or not cardholder_name:
                messages.error(request, 'Заполните все поля карты')
            else:
                # Создаем платеж с данными карты
                payment_data, payment_status, payment_error = api.create_payment(
                    order_id=order_id,
                    amount=total_amount,
                    payment_method='Card',
                    card_number=card_number,
                    card_expiry=card_expiry,
                    card_cvv=card_cvv,
                    cardholder_name=cardholder_name,
                    save_card=save_card,
                    delivery_address=delivery_address
                )
        
        if payment_status == 201:
            messages.success(request, 'Оплата успешно обработана!')
            return redirect('shop:order_detail', order_id=order_id)
        else:
            # Обработка различных типов ошибок
            if payment_data and isinstance(payment_data, dict):
                # Пытаемся извлечь понятное сообщение об ошибке
                if 'error' in payment_data:
                    error_msg = payment_data['error']
                elif 'detail' in payment_data:
                    error_msg = payment_data['detail']
                elif 'non_field_errors' in payment_data:
                    error_msg = payment_data['non_field_errors'][0] if payment_data['non_field_errors'] else 'Ошибка обработки платежа'
                else:
                    # Собираем все ошибки валидации
                    errors = []
                    for key, value in payment_data.items():
                        if isinstance(value, list):
                            errors.extend([f"{key}: {v}" for v in value])
                        else:
                            errors.append(f"{key}: {value}")
                    error_msg = '; '.join(errors) if errors else 'Ошибка обработки платежа'
            else:
                error_msg = payment_error or 'Ошибка обработки платежа'
            messages.error(request, error_msg)
    
    context = {
        'order': order,
        'total_amount': total_amount,
        'saved_cards': saved_cards,
    }
    return render(request, 'shop/payment.html', context)


def order_chat_view(request, order_id):
    """Страница чата для заказа"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    
    # Получаем информацию о заказе
    order_data, order_status, order_error = api.get_order(order_id)
    
    if order_status != 200:
        messages.error(request, order_error or 'Заказ не найден')
        return redirect('shop:orders')
    
    # Проверяем права доступа
    user_data = request.session.get('user_data', {})
    user_role = user_data.get('role_name', '')
    
    if user_role not in ('Admin', 'Analyst'):
        # Для обычных пользователей проверяем, что заказ их
        if order_data.get('user') != user_data.get('id'):
            messages.error(request, 'У вас нет доступа к этому заказу')
            return redirect('shop:orders')
        
        # Проверяем наличие активных заказов
        orders_data, orders_status, orders_error = api.get_orders()
        if orders_status == 200:
            orders = orders_data.get('results', []) if isinstance(orders_data, dict) else orders_data
            active_orders = [o for o in orders if o.get('status') in ['Pending', 'Processing', 'Shipped', 'Delivered']]
            if len(active_orders) == 0:
                messages.error(request, 'Чат доступен только при наличии активных заказов')
                return redirect('shop:orders')
    
    context = {
        'order': order_data,
        'order_id': order_id,
    }
    return render(request, 'shop/order_chat.html', context)


def order_detail(request, order_id):
    """Детали заказа"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    
    order_data, status, error = api.get_order(order_id)
    
    if status != 200:
        messages.error(request, error or 'Заказ не найден')
        return redirect('shop:orders')
    
    # Убеждаемся, что can_be_paid доступен в данных
    # Если его нет, вычисляем на основе статуса
    if 'can_be_paid' not in order_data:
        order_status = order_data.get('status', '')
        order_data['can_be_paid'] = order_status in ['Pending', 'Cancelled']
    
    # Получаем транзакции заказа
    transactions_data, transactions_status, transactions_error = api.get_order_transactions(order_id)
    transactions = []
    if transactions_status == 200 and transactions_data:
        # Обрабатываем транзакции для удобного отображения
        from datetime import datetime
        for tx in transactions_data:
            # Форматируем дату для отображения
            if isinstance(tx.get('transaction_date'), str):
                try:
                    # Парсим ISO формат даты
                    tx_date = datetime.fromisoformat(tx['transaction_date'].replace('Z', '+00:00'))
                    tx['transaction_date_formatted'] = tx_date.strftime('%d.%m.%Y %H:%M')
                except:
                    tx['transaction_date_formatted'] = tx.get('transaction_date', '')
            else:
                tx['transaction_date_formatted'] = str(tx.get('transaction_date', ''))
            transactions.append(tx)
    
    context = {
        'order': order_data,
        'transactions': transactions,
    }
    return render(request, 'shop/order_detail.html', context)


def privacy_policy(request):
    """Страница политики конфиденциальности и согласия на обработку персональных данных"""
    return render(request, 'shop/privacy.html')


def register(request):
    """Регистрация нового пользователя"""
    if request.session.get('access_token'):
        return redirect('shop:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        agree_terms = request.POST.get('agree_terms') == 'on'
        
        if not username or not email or not password1:
            messages.error(request, 'Заполните все обязательные поля')
        elif not agree_terms:
            messages.error(request, 'Необходимо согласие с политикой конфиденциальности и обработкой персональных данных')
        elif password1 != password2:
            messages.error(request, 'Пароли не совпадают')
        elif len(password1) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов')
        else:
            api = get_api_client(request)
            user_data, success, error = api.register(username, email, password1)
            
            if success:
                messages.success(
                    request,
                    'Регистрация успешна! На вашу почту отправлено письмо с подтверждением. Теперь вы можете войти.'
                )
                return redirect('shop:login')
            else:
                messages.error(request, error or 'Ошибка регистрации')
    
    return render(request, 'shop/register.html')


def password_reset_request_view(request):
    """Форма «Забыли пароль» — ввод email, отправка ссылки на почту"""
    if request.session.get('access_token'):
        return redirect('shop:home')
    
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        if not email:
            messages.error(request, 'Введите email')
        else:
            api = get_api_client(request)
            data, status, error = api.password_reset_request(email)
            # Всегда показываем нейтральное сообщение (безопасность)
            messages.success(
                request,
                'Если аккаунт с таким email существует, на него отправлена ссылка для сброса пароля. Проверьте почту.'
            )
            return redirect('shop:login')
    
    return render(request, 'shop/password_reset_request.html')


def password_reset_confirm_view(request, token):
    """Установка нового пароля по токену из ссылки в письме"""
    if request.session.get('access_token'):
        return redirect('shop:home')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password') or ''
        new_password2 = request.POST.get('new_password2') or ''
        if not new_password or len(new_password) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов')
        elif new_password != new_password2:
            messages.error(request, 'Пароли не совпадают')
        else:
            api = get_api_client(request)
            data, status, error = api.password_reset_confirm(token, new_password)
            if status == 200:
                messages.success(request, 'Пароль успешно изменён. Войдите с новым паролем.')
                return redirect('shop:login')
            err = (data or {}).get('error', error) if isinstance(data, dict) else error
            messages.error(request, err or 'Ошибка сброса пароля')
    
    return render(request, 'shop/password_reset_confirm.html', {'token': token})


def login_view(request):
    """Вход пользователя"""
    if request.session.get('access_token'):
        return redirect('shop:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Заполните все поля')
        else:
            api = get_api_client(request)
            user_data, success, error = api.login(username, password)
            
            if success:
                # Данные пользователя уже получены в методе login
                if user_data and isinstance(user_data, dict):
                    # Нормализуем данные роли для удобства использования в шаблонах
                    if 'role' in user_data and isinstance(user_data['role'], dict):
                        user_data['role_name'] = user_data['role'].get('name', '')
                    request.session['user_data'] = user_data
                else:
                    # Если данные не получены, пытаемся получить через /auth/me/
                    me_data, me_status, me_error = api.get_me()
                    if me_status == 200:
                        # Нормализуем данные роли
                        if 'role' in me_data and isinstance(me_data['role'], dict):
                            me_data['role_name'] = me_data['role'].get('name', '')
                        request.session['user_data'] = me_data
                    else:
                        # Если не удалось получить данные, сохраняем базовую информацию
                        request.session['user_data'] = {
                            'username': username,
                            'id': user_data.get('id') if isinstance(user_data, dict) else None
                        }
                
                # Получаем имя пользователя для приветствия
                display_username = user_data.get('username', username) if isinstance(user_data, dict) else username
                messages.success(request, f'Добро пожаловать, {display_username}!')
                next_url = request.GET.get('next', 'shop:home')
                return redirect(next_url)
            else:
                messages.error(request, error or 'Ошибка входа')
    
    return render(request, 'shop/login.html')


def logout_view(request):
    """Выход пользователя"""
    request.session.flush()
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('shop:home')


@require_http_methods(["GET", "POST"])
def settings_view(request):
    """Страница настроек и профиля пользователя"""
    if not request.session.get('access_token'):
        messages.error(request, 'Необходимо войти в систему')
        return redirect('shop:login')
    
    api = get_api_client(request)
    user_data = request.session.get('user_data', {})
    user_id = user_data.get('id')
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type', '')
        
        # Редактирование профиля (имя, email, смена пароля)
        if form_type == 'profile' and user_id:
            try:
                username = (request.POST.get('profile_username') or '').strip()
                email = (request.POST.get('profile_email') or '').strip()
                new_password = request.POST.get('profile_new_password') or ''
                new_password2 = request.POST.get('profile_new_password2') or ''
                
                if not username:
                    messages.error(request, 'Укажите имя пользователя')
                elif not email:
                    messages.error(request, 'Укажите email')
                else:
                    if new_password or new_password2:
                        if len(new_password) < 8:
                            messages.error(request, 'Новый пароль должен быть не короче 8 символов')
                        elif new_password != new_password2:
                            messages.error(request, 'Пароли не совпадают')
                        else:
                            profile_data = {'username': username, 'email': email, 'password': new_password}
                            response_data, status, error = api.update_user(user_id, profile_data)
                            if status == 200:
                                messages.success(request, 'Профиль и пароль успешно сохранены')
                                me_data, me_status, _ = api.get_me()
                                if me_status == 200:
                                    request.session['user_data'] = me_data
                                    request.session.save()
                                return redirect('shop:settings')
                            _add_profile_error(request, response_data, error, 'Ошибка сохранения профиля')
                    else:
                        profile_data = {'username': username, 'email': email}
                        response_data, status, error = api.update_user(user_id, profile_data)
                        if status == 200:
                            messages.success(request, 'Профиль успешно сохранён')
                            me_data, me_status, _ = api.get_me()
                            if me_status == 200:
                                request.session['user_data'] = me_data
                                request.session.save()
                            return redirect('shop:settings')
                        _add_profile_error(request, response_data, error, 'Ошибка сохранения профиля')
            except ValueError:
                messages.error(request, 'Необходимо войти в систему')
                return redirect('shop:login')
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception('Ошибка при сохранении профиля')
                messages.error(request, f'Ошибка при сохранении профиля: {str(e)}')
            # После ошибки продолжаем показывать страницу (ниже отрисуется форма с контекстом)
        
        # Обновление настроек приложения (форма по умолчанию)
        elif form_type != 'profile':
            try:
                settings_data = {
                    'date_format': request.POST.get('date_format', 'DD.MM.YYYY'),
                    'number_format': request.POST.get('number_format', 'ru'),
                    'page_size': int(request.POST.get('page_size', 20)),
                }
                catalog_filters = {}
                if request.POST.get('catalog_filter_category'):
                    catalog_filters['category'] = request.POST.get('catalog_filter_category')
                if request.POST.get('catalog_filter_search'):
                    catalog_filters['search'] = request.POST.get('catalog_filter_search')
                if catalog_filters:
                    settings_data['catalog_filters'] = catalog_filters
                response_data, status, error = api.update_user_settings(settings_data)
                if status == 200:
                    messages.success(request, 'Настройки успешно сохранены')
                    me_data, me_status, me_error = api.get_me()
                    if me_status == 200:
                        request.session['user_data'] = me_data
                        if 'settings' not in request.session['user_data']:
                            request.session['user_data']['settings'] = response_data
                        else:
                            if isinstance(request.session['user_data']['settings'], dict):
                                request.session['user_data']['settings'].update(response_data)
                            else:
                                request.session['user_data']['settings'] = response_data
                        request.session.save()
                    else:
                        if 'user_data' in request.session:
                            if 'settings' not in request.session['user_data']:
                                request.session['user_data']['settings'] = response_data
                            else:
                                if isinstance(request.session['user_data']['settings'], dict):
                                    request.session['user_data']['settings'].update(response_data)
                                else:
                                    request.session['user_data']['settings'] = response_data
                            request.session.save()
                    return redirect('shop:settings')
                else:
                    error_message = 'Ошибка сохранения настроек'
                    if error:
                        error_message = error
                    elif response_data and isinstance(response_data, dict):
                        if 'detail' in response_data:
                            error_message = response_data['detail']
                        elif 'error' in response_data:
                            error_message = response_data['error']
                        elif 'non_field_errors' in response_data:
                            error_message = '; '.join(response_data['non_field_errors'])
                    messages.error(request, error_message)
            except ValueError as e:
                messages.error(request, 'Необходимо войти в систему для сохранения настроек')
                return redirect('shop:login')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Ошибка при сохранении настроек: {e}', exc_info=True)
                messages.error(request, f'Произошла ошибка при сохранении настроек: {str(e)}')
    
    # Получаем текущие настройки
    settings_data, status, error = api.get_user_settings()
    
    if status != 200:
        settings_data = {
            'date_format': 'DD.MM.YYYY',
            'number_format': 'ru',
            'page_size': 20,
            'catalog_filters': {},
            'analytics_filters': {},
        }
    
    # Обновляем настройки в сессии для использования в других шаблонах
    if 'user_data' in request.session:
        if not request.session['user_data'].get('settings'):
            request.session['user_data']['settings'] = settings_data
        else:
            # Обновляем только если настройки изменились
            request.session['user_data']['settings'].update(settings_data)
        request.session.save()
    
    context = {
        'settings': settings_data,
        'user_data': user_data,
    }
    return render(request, 'shop/settings.html', context)