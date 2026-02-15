"""
Views для админ-панели и аналитики
"""
import io
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from .api_client import APIClient
from .views import _format_order_date
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation


def get_api_client(request):
    """Получить API клиент с сессией"""
    return APIClient(session=request.session)


def check_role(request, allowed_roles):
    """
    Проверить роль пользователя
    
    Args:
        request: HTTP request
        allowed_roles: список разрешенных ролей (например, ['Admin', 'Analyst'])
    
    Returns:
        tuple: (is_allowed, user_data)
    """
    if not request.session.get('access_token'):
        return False, None
    
    user_data = request.session.get('user_data', {})
    # Проверяем роль через role_name или role.name
    user_role = user_data.get('role_name', '')
    if not user_role and 'role' in user_data:
        if isinstance(user_data['role'], dict):
            user_role = user_data['role'].get('name', '')
        else:
            user_role = str(user_data['role'])
    
    return user_role in allowed_roles, user_data


def analytics_dashboard(request):
    """Дашборд аналитики"""
    is_allowed, user_data = check_role(request, ['Admin', 'Analyst'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Analyst или Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Получаем статистику дашборда
    stats_data, status, error = api.get_dashboard_stats()
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки статистики')
        stats_data = {
            'total_revenue': 0,
            'total_orders': 0,
            'active_users': 0,
            'top_products': []
        }
    
    context = {
        'stats': stats_data,
        'user_role': user_data.get('role', ''),
    }
    return render(request, 'shop/analytics/dashboard.html', context)


def sales_by_product(request):
    """Продажи по продуктам"""
    is_allowed, user_data = check_role(request, ['Admin', 'Analyst'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Analyst или Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Параметры фильтрации
    category_id = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Если даты не указаны, используем последние 30 дней
    if not date_from or not date_to:
        date_to = datetime.now().date()
        date_from = date_to - timedelta(days=30)
        date_from = date_from.isoformat()
        date_to = date_to.isoformat()
    
    sales_data, status, error = api.get_sales_by_product(
        category_id=int(category_id) if category_id else None,
        date_from=date_from,
        date_to=date_to
    )
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки данных')
        sales_data = []
    
    # Приводим к списку
    sales_list = sales_data if isinstance(sales_data, list) else []
    
    # Считаем итоги на сервере с устойчивым парсингом (числа, Decimal и строки с ₽/запятыми)
    def parse_decimal_value(value):
        if value is None:
            return Decimal('0')
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            cleaned = (
                value.replace('\xa0', '')
                .replace(' ', '')
                .replace('₽', '')
                .replace('руб.', '')
                .replace(',', '.')
            )
            cleaned = ''.join(ch for ch in cleaned if ch.isdigit() or ch in '.-')
            if not cleaned or cleaned in {'.', '-', '-.'}:
                return Decimal('0')
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                return Decimal('0')
        return Decimal('0')

    def parse_int_value(value):
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, Decimal):
            return int(value)
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            digits = ''.join(ch for ch in value if ch.isdigit())
            return int(digits) if digits else 0
        return 0

    total_revenue = Decimal('0')
    total_quantity = 0
    for sale in sales_list:
        total_revenue += parse_decimal_value(
            sale.get('total_revenue', sale.get('total_amount', 0))
        )
        total_quantity += parse_int_value(
            sale.get('total_quantity_sold', sale.get('total_quantity', 0))
        )
    
    # Получаем категории для фильтра
    categories_data, cat_status, cat_error = api.get_categories()
    categories = categories_data.get('results', []) if cat_status == 200 else []
    
    # Конвертируем данные в JSON для JavaScript графиков
    sales_json = json.dumps(sales_list, ensure_ascii=False, default=str)
    
    context = {
        'sales': sales_list,
        'sales_json': sales_json,
        'total_revenue': f'{total_revenue:.2f}',
        'total_quantity': total_quantity,
        'categories': categories,
        'selected_category': int(category_id) if category_id else None,
        'date_from': date_from,
        'date_to': date_to,
        'user_role': user_data.get('role', ''),
    }
    return render(request, 'shop/analytics/sales_by_product.html', context)


def admin_download_backup(request, backup_id):
    """Скачать резервную копию через веб-интерфейс (проксирование API)."""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')

    import requests
    from django.conf import settings
    from django.http import HttpResponse

    # URL без завершающего слэша — бэкенд ожидает слэш (Django APPEND_SLASH)
    base = (getattr(settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1') or '').rstrip('/')
    api_url = f"{base}/admin/backups/{backup_id}/download/"
    token = request.session.get('access_token')
    if not token:
        messages.error(request, 'Требуется авторизация. Выполните вход снова.')
        return redirect('shop:admin_backups')
    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.get(api_url, headers=headers, timeout=120)
        if response.status_code != 200:
            # Пытаемся показать текст ошибки от API
            try:
                err = response.json()
                msg = err.get('error') or err.get('detail') or f'Ошибка скачивания: {response.status_code}'
            except Exception:
                msg = response.text or f'Ошибка скачивания бекапа: {response.status_code}'
            messages.error(request, msg)
            return redirect('shop:admin_backups')

        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        content_disposition = response.headers.get('Content-Disposition', '')
        if not content_disposition:
            content_disposition = f'attachment; filename="backup_{backup_id}.dump"'

        download_response = HttpResponse(response.content, content_type=content_type)
        download_response['Content-Disposition'] = content_disposition
        return download_response
    except requests.exceptions.ConnectionError as e:
        messages.error(
            request,
            'Не удалось подключиться к API. Проверьте, что сервер API запущен (порт 8000) и API_BASE_URL в настройках веб-сайта указан верно.'
        )
        return redirect('shop:admin_backups')
    except Exception as e:
        messages.error(request, f'Ошибка при скачивании бекапа: {str(e)}')
        return redirect('shop:admin_backups')


def monthly_sales(request):
    """Ежемесячные продажи"""
    is_allowed, user_data = check_role(request, ['Admin', 'Analyst'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Analyst или Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    year = request.GET.get('year', datetime.now().year)
    
    sales_data, status, error = api.get_monthly_sales(year=int(year) if year else None)
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки данных')
        sales_data = []
    
    sales_list = sales_data if isinstance(sales_data, list) else []
    sales_json = json.dumps(sales_list, ensure_ascii=False, default=str)
    
    context = {
        'sales': sales_list,
        'sales_json': sales_json,
        'year': year,
        'user_role': user_data.get('role', ''),
    }
    return render(request, 'shop/analytics/monthly_sales.html', context)


def top_products(request):
    """Топ товаров"""
    is_allowed, user_data = check_role(request, ['Admin', 'Analyst'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Analyst или Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    limit = int(request.GET.get('limit', 10))
    
    products_data, status, error = api.get_top_products(limit=limit)
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки данных')
        products_data = []
    
    context = {
        'products': products_data if isinstance(products_data, list) else [],
        'limit': limit,
        'user_role': user_data.get('role', ''),
    }
    return render(request, 'shop/analytics/top_products.html', context)


def revenue(request):
    """Выручка за период"""
    is_allowed, user_data = check_role(request, ['Admin', 'Analyst'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Analyst или Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Если даты не указаны, используем последние 30 дней
    if not date_from or not date_to:
        date_to = datetime.now().date()
        date_from = date_to - timedelta(days=30)
        date_from = date_from.isoformat()
        date_to = date_to.isoformat()
    
    revenue_data, status, error = api.get_revenue(date_from, date_to)
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки данных')
        revenue_data = []
    
    revenue_list = revenue_data if isinstance(revenue_data, list) else []
    revenue_json = json.dumps(revenue_list, ensure_ascii=False, default=str)
    total_revenue_sum = sum(
        Decimal(str(item.get('revenue', 0) or 0)) for item in revenue_list
    )
    
    context = {
        'revenue': revenue_list,
        'revenue_json': revenue_json,
        'date_from': date_from,
        'date_to': date_to,
        'total_revenue_sum': total_revenue_sum,
        'user_role': user_data.get('role', ''),
    }
    return render(request, 'shop/analytics/revenue.html', context)


# Admin views
def admin_dashboard(request):
    """Админ-панель"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Получаем статистику
    stats_data, status, error = api.get_dashboard_stats()
    
    if status != 200:
        stats_data = {
            'total_revenue': 0,
            'total_orders': 0,
            'active_users': 0,
            'top_products': []
        }
    
    context = {
        'stats': stats_data,
        'user_role': user_data.get('role', ''),
    }
    return render(request, 'shop/admin/dashboard.html', context)


def admin_products(request):
    """Управление товарами"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Обработка импорта CSV
    if request.method == 'POST' and 'import_csv' in request.POST:
        import requests
        from django.conf import settings as django_settings
        
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            api_base_url = getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1')
            api_url = f"{api_base_url}/products/import/csv/"
            
            # Отправляем файл на API
            files = {'file': (csv_file.name, csv_file, 'text/csv')}
            headers = {'Authorization': f'Bearer {request.session.get("access_token")}'}
            
            try:
                response = requests.post(api_url, files=files, headers=headers, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('has_errors'):
                        messages.warning(request, 
                            f'Импорт завершен с ошибками. Создано: {result.get("created", 0)}, '
                            f'Обновлено: {result.get("updated", 0)}, Ошибок: {len(result.get("errors", []))}')
                    else:
                        messages.success(request, 
                            f'Импорт успешно завершен. Создано: {result.get("created", 0)}, '
                            f'Обновлено: {result.get("updated", 0)}')
                else:
                    error_data = response.json() if response.content else {}
                    messages.error(request, error_data.get('error', 'Ошибка импорта'))
            except Exception as e:
                messages.error(request, f'Ошибка при импорте: {str(e)}')
    
    # Получаем товары (в админ-панели показываем все товары, включая недоступные)
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    
    products_data, status, error = api.get_products(page=page, page_size=50, available_only=False)
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки товаров')
        products = {'results': [], 'count': 0, 'next': None, 'previous': None}
    else:
        products = products_data
    
    # Получаем категории
    categories_data, cat_status, cat_error = api.get_categories()
    categories = categories_data.get('results', []) if cat_status == 200 else []
    
    from django.conf import settings as django_settings
    from urllib.parse import urlparse, parse_qs, urlencode
    
    # Преобразуем API URL пагинации в веб-URL
    def convert_pagination_url(api_url):
        if not api_url:
            return None
        try:
            parsed = urlparse(api_url)
            params = parse_qs(parsed.query)
            page_num = params.get('page', [None])[0]
            if page_num:
                query_params = {'page': page_num}
                web_url = request.path + '?' + urlencode(query_params)
                return web_url
        except Exception:
            pass
        return None
    
    # Преобразуем next и previous
    pagination = {}
    if products.get('next'):
        pagination['next'] = convert_pagination_url(products['next'])
    if products.get('previous'):
        pagination['previous'] = convert_pagination_url(products['previous'])
    
    context = {
        'products': products.get('results', []),
        'products_pagination': pagination,
        'products_count': products.get('count', 0),
        'current_page': page,
        'categories': categories,
        'user_role': user_data.get('role', ''),
        'api_base_url': getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
    }
    return render(request, 'shop/admin/products.html', context)


def admin_categories(request):
    """Управление категориями"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Обработка импорта CSV
    if request.method == 'POST' and 'import_csv' in request.POST:
        import requests
        from django.conf import settings
        
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            api_url = f"{settings.API_BASE_URL}/categories/import/csv/"
            
            files = {'file': (csv_file.name, csv_file, 'text/csv')}
            headers = {'Authorization': f'Bearer {request.session.get("access_token")}'}
            
            try:
                response = requests.post(api_url, files=files, headers=headers, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('has_errors'):
                        messages.warning(request, 
                            f'Импорт завершен с ошибками. Создано: {result.get("created", 0)}, '
                            f'Обновлено: {result.get("updated", 0)}, Ошибок: {len(result.get("errors", []))}')
                    else:
                        messages.success(request, 
                            f'Импорт успешно завершен. Создано: {result.get("created", 0)}, '
                            f'Обновлено: {result.get("updated", 0)}')
                else:
                    error_data = response.json() if response.content else {}
                    messages.error(request, error_data.get('error', 'Ошибка импорта'))
            except Exception as e:
                messages.error(request, f'Ошибка при импорте: {str(e)}')
    
    # Получаем категории
    categories_data, status, error = api.get_categories()
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки категорий')
        categories = []
    else:
        categories = categories_data.get('results', []) if isinstance(categories_data, dict) else categories_data
    
    from django.conf import settings as django_settings
    
    context = {
        'categories': categories if isinstance(categories, list) else [],
        'user_role': user_data.get('role', ''),
        'api_base_url': getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
    }
    return render(request, 'shop/admin/categories.html', context)


def admin_export_categories_csv(request):
    """Экспорт категорий в CSV через веб-интерфейс"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    import requests
    from django.conf import settings
    from django.http import HttpResponse
    
    api_url = f"{settings.API_BASE_URL}/categories/export/csv/"
    headers = {'Authorization': f'Bearer {request.session.get("access_token")}'}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Создаем HTTP ответ с CSV
            csv_response = HttpResponse(
                response.content,
                content_type='text/csv; charset=utf-8'
            )
            csv_response['Content-Disposition'] = 'attachment; filename="categories_export.csv"'
            return csv_response
        else:
            messages.error(request, f'Ошибка экспорта: {response.status_code}')
            return redirect('shop:admin_categories')
    except Exception as e:
        messages.error(request, f'Ошибка при экспорте: {str(e)}')
        return redirect('shop:admin_categories')


def admin_export_products_csv(request):
    """Экспорт товаров в CSV через веб-интерфейс"""
    is_allowed, user_data = check_role(request, ['Admin', 'Analyst'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin или Analyst')
        return redirect('shop:home')
    
    import requests
    from django.conf import settings
    from django.http import HttpResponse
    
    api_url = f"{settings.API_BASE_URL}/products/export/csv/"
    headers = {'Authorization': f'Bearer {request.session.get("access_token")}'}
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Создаем HTTP ответ с CSV
            csv_response = HttpResponse(
                response.content,
                content_type='text/csv; charset=utf-8'
            )
            csv_response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
            return csv_response
        else:
            messages.error(request, f'Ошибка экспорта: {response.status_code}')
            return redirect('shop:admin_products')
    except Exception as e:
        messages.error(request, f'Ошибка при экспорте: {str(e)}')
        return redirect('shop:admin_products')


def analytics_export_csv(request, report_type):
    """
    Прокси экспорта отчётов аналитики в CSV (вызов API с токеном, возврат файла).
    report_type: 'sales-by-product' | 'monthly-sales' | 'revenue' | 'top-products'
    """
    is_allowed, _ = check_role(request, ['Admin', 'Analyst'])
    if not is_allowed:
        from django.http import HttpResponse
        return HttpResponse('Доступ запрещен', status=403)
    import requests
    from django.conf import settings
    from django.http import HttpResponse
    base = getattr(settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1').rstrip('/')
    query = request.GET.urlencode()
    api_url = f"{base}/analytics/{report_type}/export/csv/"
    if query:
        api_url += '?' + query
    headers = {'Authorization': f'Bearer {request.session.get("access_token")}'}
    filenames = {
        'sales-by-product': 'sales_by_product_export.csv',
        'monthly-sales': 'monthly_sales_export.csv',
        'revenue': 'revenue_export.csv',
        'top-products': 'top_products_export.csv',
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return HttpResponse(f'Ошибка экспорта: {resp.status_code}', status=502)
        response = HttpResponse(resp.content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filenames.get(report_type, "export.csv")}"'
        return response
    except Exception as e:
        return HttpResponse(f'Ошибка при экспорте: {str(e)}', status=500)


def admin_users(request):
    """Управление пользователями"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Поиск по пользователям (имя, email)
    search_query = request.GET.get('search', '').strip()
    
    # Получаем пользователей (с опциональным поиском)
    users_data, status, error = api.get_users(search=search_query if search_query else None)
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки пользователей')
        users = []
    else:
        if users_data is None:
            users = []
        elif isinstance(users_data, list):
            users = users_data
        elif isinstance(users_data, dict):
            users = users_data.get('results', [])
        else:
            users = []
    
    # Получаем роли для выпадающего списка
    roles_data, roles_status, roles_error = api.get_roles()
    roles = roles_data.get('results', []) if roles_status == 200 and isinstance(roles_data, dict) else []
    
    # Форматируем дату регистрации для отображения в таблице
    from datetime import datetime
    for u in (users if isinstance(users, list) else []):
        if isinstance(u, dict) and u.get('created_at'):
            try:
                raw = u['created_at']
                if isinstance(raw, str):
                    dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                    u['created_at_formatted'] = dt.strftime('%d.%m.%Y')
                else:
                    u['created_at_formatted'] = raw.strftime('%d.%m.%Y') if hasattr(raw, 'strftime') else str(raw)
            except (ValueError, TypeError, AttributeError):
                u['created_at_formatted'] = str(u.get('created_at', '-'))
        elif isinstance(u, dict):
            u['created_at_formatted'] = '-'
    
    from django.conf import settings as django_settings
    
    context = {
        'users': users if isinstance(users, list) else [],
        'roles': roles if isinstance(roles, list) else [],
        'user_role': user_data.get('role', ''),
        'api_base_url': getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
        'search_query': search_query,
    }
    return render(request, 'shop/admin/users.html', context)


def admin_orders(request):
    """Управление заказами"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Получаем заказы (для админа - все заказы)
    orders_data, status, error = api.get_orders()
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки заказов')
        orders = []
    else:
        orders = orders_data.get('results', []) if isinstance(orders_data, dict) else orders_data
        for order in orders:
            if isinstance(order, dict):
                order['order_date_display'] = _format_order_date(
                    order.get('order_date') or order.get('created_at')
                )
    
    from django.conf import settings as django_settings
    
    context = {
        'orders': orders if isinstance(orders, list) else [],
        'user_role': user_data.get('role', ''),
        'api_base_url': getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
    }
    return render(request, 'shop/admin/orders.html', context)


def admin_transactions(request):
    """Управление транзакциями"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Получаем все заказы для извлечения транзакций
    orders_data, status, error = api.get_orders()
    
    transactions = []
    if status == 200:
        orders = orders_data.get('results', []) if isinstance(orders_data, dict) else orders_data
        # Собираем все транзакции из заказов
        for order in orders:
            if order.get('id'):
                tx_data, tx_status, tx_error = api.get_order_transactions(order['id'])
                if tx_status == 200 and tx_data:
                    if isinstance(tx_data, list):
                        transactions.extend(tx_data)
                    else:
                        transactions.append(tx_data)
    
    # Форматируем дату транзакции для отображения в таблице
    from datetime import datetime
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        raw = tx.get('transaction_date') or tx.get('created_at')
        if raw:
            try:
                if isinstance(raw, str):
                    dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                    tx['transaction_date_formatted'] = dt.strftime('%d.%m.%Y %H:%M')
                else:
                    tx['transaction_date_formatted'] = raw.strftime('%d.%m.%Y %H:%M') if hasattr(raw, 'strftime') else str(raw)
            except (ValueError, TypeError, AttributeError):
                tx['transaction_date_formatted'] = str(raw)
        else:
            tx['transaction_date_formatted'] = '-'
    
    from django.conf import settings as django_settings
    
    context = {
        'transactions': transactions,
        'user_role': user_data.get('role', ''),
        'api_base_url': getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
    }
    return render(request, 'shop/admin/transactions.html', context)


def admin_cart_items(request):
    """Управление корзиной"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Получаем список пользователей для выбора
    users_data, users_status, users_error = api.get_users()
    users = []
    if users_status == 200:
        users = users_data.get('results', []) if isinstance(users_data, dict) else users_data
    
    # Получаем корзину выбранного пользователя или текущего
    selected_user_id = request.GET.get('user_id')
    cart_items = []
    selected_user = None
    
    if selected_user_id:
        try:
            user_id = int(selected_user_id)
            cart_data, status, error = api.get_user_cart(user_id)
            if status == 200:
                cart_items = cart_data.get('items', [])
                selected_user = cart_data.get('user_username', f'ID: {user_id}')
        except (ValueError, TypeError):
            pass
    
    from django.conf import settings as django_settings
    
    context = {
        'cart_items': cart_items if isinstance(cart_items, list) else [],
        'users': users if isinstance(users, list) else [],
        'selected_user_id': selected_user_id,
        'selected_user': selected_user,
        'user_role': user_data.get('role', ''),
        'api_base_url': getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
    }
    return render(request, 'shop/admin/cart_items.html', context)


def analytics_reports(request):
    """Окно с отчетами для аналитика"""
    is_allowed, user_data = check_role(request, ['Analyst'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Analyst')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Получаем различные отчеты
    dashboard_stats, stats_status, stats_error = api.get_dashboard_stats()
    top_products_data, top_status, top_error = api.get_top_products(limit=10)
    
    # API /analytics/top-products/ возвращает список, не словарь с results
    if top_status == 200 and isinstance(top_products_data, list):
        top_products_list = top_products_data
    elif top_status == 200 and isinstance(top_products_data, dict):
        top_products_list = top_products_data.get('results', [])
    else:
        top_products_list = []
    
    stats = dashboard_stats if stats_status == 200 else {}
    # Средний чек: считаем во вьюхе (в шаблоне нет фильтра div)
    total_revenue = stats.get('total_revenue') or 0
    total_orders = stats.get('total_orders') or 0
    try:
        total_revenue = Decimal(str(total_revenue))
    except (InvalidOperation, TypeError):
        total_revenue = Decimal('0')
    if total_orders and int(total_orders) > 0:
        stats['avg_check'] = (total_revenue / int(total_orders)).quantize(Decimal('0.01'))
    else:
        stats['avg_check'] = Decimal('0')
    
    context = {
        'stats': stats,
        'top_products': top_products_list,
        'user_role': user_data.get('role_name', 'Analyst'),
    }
    return render(request, 'shop/analytics/reports.html', context)


# Admin views для логов, аудита и бэкапов
def admin_logs(request):
    """Просмотр операционных логов"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Параметры фильтрации
    level = request.GET.get('level')
    user_id = request.GET.get('user_id')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    page = int(request.GET.get('page', 1))
    
    logs_data, status, error = api.get_logs(
        level=level,
        user_id=int(user_id) if user_id else None,
        date_from=date_from,
        date_to=date_to,
        page=page
    )
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки логов')
        logs_data = {'results': [], 'count': 0}
    
    logs_list = logs_data.get('results', []) if isinstance(logs_data, dict) else logs_data
    for log in logs_list:
        if isinstance(log, dict):
            log['ts_display'] = _format_log_ts(log.get('ts'))
    
    context = {
        'logs': logs_list,
        'pagination': logs_data if isinstance(logs_data, dict) else {},
        'filters': {
            'level': level,
            'user_id': user_id,
            'date_from': date_from,
            'date_to': date_to,
        },
        'user_role': user_data.get('role_name', 'Admin'),
    }
    return render(request, 'shop/admin/logs.html', context)


def _format_log_ts(ts):
    """Форматирует время лога из API (ISO-строка или объект) в строку дд.мм.гггг чч:мм:сс."""
    if not ts:
        return '—'
    if hasattr(ts, 'strftime'):
        return ts.strftime('%d.%m.%Y %H:%M:%S')
    s = str(ts).strip()
    if not s:
        return '—'
    try:
        s = s.replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        return dt.strftime('%d.%m.%Y %H:%M:%S')
    except (ValueError, TypeError):
        return s[:19] if len(s) >= 19 else s


def admin_logs_export_pdf(request):
    """Экспорт операционных логов в PDF."""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    level = request.GET.get('level')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    api = get_api_client(request)
    logs_data, status, error = api.get_logs(
        level=level,
        date_from=date_from,
        date_to=date_to,
        page=1,
        page_size=500
    )
    logs = []
    if status == 200 and isinstance(logs_data, dict):
        logs = logs_data.get('results', [])
    elif status == 200 and isinstance(logs_data, list):
        logs = logs_data
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
    except ImportError:
        messages.error(request, 'Модуль reportlab не установлен. Установите: pip install reportlab')
        return redirect('shop:admin_logs')
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph('Операционные логи — SportShop', styles['Title']))
    elements.append(Spacer(1, 8 * mm))
    filter_info = []
    if level:
        filter_info.append(f'Уровень: {level}')
    if date_from:
        filter_info.append(f'Дата от: {date_from}')
    if date_to:
        filter_info.append(f'Дата до: {date_to}')
    if filter_info:
        elements.append(Paragraph('Фильтры: ' + ', '.join(filter_info), styles['Normal']))
        elements.append(Spacer(1, 4 * mm))
    data = [['ID', 'Время', 'Уровень', 'Сообщение', 'Пользователь', 'IP']]
    for log in logs:
        if not isinstance(log, dict):
            continue
        user_name = '—'
        if log.get('user'):
            u = log['user']
            user_name = u.get('username', u.get('id', '—')) if isinstance(u, dict) else str(u)
        msg = (log.get('message') or '')[:80]
        if len(log.get('message') or '') > 80:
            msg += '…'
        data.append([
            str(log.get('id', '')),
            _format_log_ts(log.get('ts')),
            log.get('level', ''),
            msg,
            user_name,
            log.get('ip_address') or '—'
        ])
    if len(data) == 1:
        data.append(['Нет записей', '', '', '', '', ''])
    table = Table(data, colWidths=[25, 45, 35, 180, 55, 45])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = 'operational_logs.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def admin_audit(request):
    """Просмотр журнала аудита"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    # Получаем список пользователей для фильтра
    users_data, users_status, users_error = api.get_users()
    users = []
    if users_status == 200:
        users = users_data.get('results', []) if isinstance(users_data, dict) else users_data
    
    # Параметры фильтрации
    action = request.GET.get('action')
    table_name = request.GET.get('table_name')
    user_id = request.GET.get('user_id')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    
    # Преобразуем user_id в int только если он есть и валиден
    user_id_int = None
    if user_id:
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            user_id_int = None
    
    audit_data, status, error = api.get_audit_logs(
        action=action,
        table_name=table_name,
        user_id=user_id_int,
        date_from=date_from,
        date_to=date_to,
        page=page
    )
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки аудита')
        audit_data = {'results': [], 'count': 0}
    
    # Обрабатываем пагинацию - извлекаем номер страницы из URL
    pagination = {}
    if isinstance(audit_data, dict):
        if 'next' in audit_data and audit_data['next']:
            # Извлекаем номер страницы из URL
            next_url = audit_data['next']
            if 'page=' in next_url:
                try:
                    page_num = int(next_url.split('page=')[1].split('&')[0])
                    # Сохраняем все параметры фильтрации
                    params = request.GET.copy()
                    params['page'] = page_num
                    pagination['next'] = '?' + params.urlencode()
                except (ValueError, IndexError):
                    pagination['next'] = audit_data['next']
            else:
                pagination['next'] = audit_data['next']
        if 'previous' in audit_data and audit_data['previous']:
            prev_url = audit_data['previous']
            if 'page=' in prev_url:
                try:
                    page_num = int(prev_url.split('page=')[1].split('&')[0])
                    # Сохраняем все параметры фильтрации
                    params = request.GET.copy()
                    params['page'] = page_num
                    pagination['previous'] = '?' + params.urlencode()
                except (ValueError, IndexError):
                    pagination['previous'] = audit_data['previous']
            else:
                pagination['previous'] = audit_data['previous']
    
    from django.conf import settings as django_settings
    
    context = {
        'audit_logs': audit_data.get('results', []) if isinstance(audit_data, dict) else audit_data,
        'pagination': pagination,
        'users': users if isinstance(users, list) else [],
        'filters': {
            'action': action,
            'table_name': table_name,
            'user_id': user_id,
            'date_from': date_from,
            'date_to': date_to,
        },
        'user_role': user_data.get('role_name', 'Admin'),
        'api_base_url': getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
    }
    return render(request, 'shop/admin/audit.html', context)


def admin_backups(request):
    """Управление резервными копиями"""
    is_allowed, user_data = check_role(request, ['Admin'])
    if not is_allowed:
        messages.error(request, 'Доступ запрещен. Требуется роль Admin')
        return redirect('shop:home')
    
    api = get_api_client(request)
    
    if request.method == 'POST':
        if 'create_backup' in request.POST:
            description = request.POST.get('description', '')
            backup_data, status, error = api.create_backup(description=description if description else None)
            
            if status == 201:
                messages.success(request, 'Резервная копия успешно создана')
            else:
                messages.error(request, error or 'Ошибка создания резервной копии')
        
        elif 'restore_backup' in request.POST:
            backup_id = request.POST.get('backup_id')
            if backup_id:
                restore_data, status, error = api.restore_backup(int(backup_id))
                
                if status == 200:
                    messages.success(request, 'База данных успешно восстановлена из резервной копии')
                else:
                    messages.error(request, error or 'Ошибка восстановления')
        
        elif 'save_schedule' in request.POST:
            schedule_data = {
                'is_enabled': request.POST.get('schedule_enabled') == 'on',
                'frequency': request.POST.get('schedule_frequency', 'daily'),
                'time': request.POST.get('schedule_time', '02:00'),
                'keep_days': int(request.POST.get('schedule_keep_days', 30)),
            }
            schedule_resp, sched_status, sched_error = api.update_backup_schedule(schedule_data)
            
            if sched_status == 200:
                messages.success(request, 'Расписание автоматических бекапов сохранено')
            else:
                messages.error(request, sched_error or 'Ошибка сохранения расписания')
    
    # Получаем список бэкапов
    backups_data, status, error = api.get_backups()
    
    if status != 200:
        messages.error(request, error or 'Ошибка загрузки резервных копий')
        backups = []
    else:
        backups = backups_data.get('results', []) if isinstance(backups_data, dict) else backups_data
    
    # Получаем расписание бекапов
    schedule_data, sched_status, sched_error = api.get_backup_schedule()
    if sched_status != 200:
        schedule_data = {
            'is_enabled': False,
            'frequency': 'daily',
            'time': '02:00',
            'keep_days': 30,
        }
    
    from django.conf import settings as django_settings
    
    context = {
        'backups': backups if isinstance(backups, list) else [],
        'schedule': schedule_data,
        'user_role': user_data.get('role_name', 'Admin'),
        'api_base_url': getattr(django_settings, 'API_BASE_URL', 'http://127.0.0.1:8000/api/v1'),
    }
    return render(request, 'shop/admin/backups.html', context)
