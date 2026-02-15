"""
Сервис аналитики: запросы к БД, представлениям и функциям, кэширование.
"""
from django.db import connection
from django.core.cache import cache
from .serializers import (
    SalesByProductSerializer,
    MonthlySalesSerializer,
    TopProductsSerializer,
    RevenueSerializer
)


class AnalyticsService:
    CACHE_TIMEOUT = 900
    
    @staticmethod
    def get_sales_by_product(category_id=None, date_from=None, date_to=None):
        """
        Получить продажи по продуктам.
        При указании дат — агрегат за период из order_items/orders; иначе — из представления v_sales_by_product.
        
        Args:
            category_id: фильтр по категории (опционально)
            date_from: начало периода (опционально)
            date_to: конец периода (опционально)
        
        Returns:
            list: список словарей с данными о продажах
        """
        cache_key = f'sales_by_product_{category_id}_{date_from}_{date_to}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        use_date_filter = date_from or date_to

        if use_date_filter:
            query = """
                SELECT
                    p.id AS product_id,
                    p.name AS product_name,
                    SUM(oi.quantity)::integer AS total_quantity_sold,
                    SUM(oi.quantity * oi.price_at_purchase) AS total_revenue
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                JOIN products p ON p.id = oi.product_id
                WHERE o.status = 'Completed'
            """
            params = []
            date_conditions = []
            if date_from:
                date_conditions.append("o.order_date::date >= %s")
                params.append(date_from)
            if date_to:
                date_conditions.append("o.order_date::date <= %s")
                params.append(date_to)
            if date_conditions:
                query += " AND " + " AND ".join(date_conditions)
            if category_id:
                query += " AND p.category_id = %s"
                params.append(category_id)
            query += " GROUP BY p.id, p.name ORDER BY total_revenue DESC"
        else:
            query = """
                SELECT
                    product_id,
                    product_name,
                    total_quantity_sold,
                    total_revenue
                FROM v_sales_by_product
            """
            params = []
            conditions = []
            if category_id:
                conditions.append("product_id IN (SELECT id FROM products WHERE category_id = %s)")
                params.append(category_id)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY total_revenue DESC"

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cache.set(cache_key, results, AnalyticsService.CACHE_TIMEOUT)
        return results
    
    @staticmethod
    def get_monthly_sales(year=None):
        """
        Получить ежемесячные продажи из представления v_monthly_sales
        
        Args:
            year: фильтр по году (опционально)
        
        Returns:
            list: список словарей с данными о продажах
        """
        cache_key = f'monthly_sales_{year}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        query = """
            SELECT 
                month_start,
                total_revenue,
                orders_count
            FROM shop.v_monthly_sales
        """
        params = []
        
        if year:
            query += " WHERE EXTRACT(YEAR FROM month_start) = %s"
            params.append(year)
        
        query += " ORDER BY month_start DESC"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
        
        cache.set(cache_key, results, AnalyticsService.CACHE_TIMEOUT)
        return results
    
    @staticmethod
    def get_top_products(limit=10):
        """
        Получить топ товаров через функцию БД fn_top_products
        
        Args:
            limit: количество товаров (по умолчанию 10)
        
        Returns:
            list: список словарей с данными о товарах
        """
        cache_key = f'top_products_{limit}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        with connection.cursor() as cursor:
            cursor.callproc('fn_top_products', [limit])
            results = []
            for row in cursor.fetchall():
                results.append({
                    'product_id': row[0],
                    'product_name': row[1],
                    'qty_sold': row[2]
                })
        
        cache.set(cache_key, results, AnalyticsService.CACHE_TIMEOUT)
        return results
    
    @staticmethod
    def get_revenue_between(date_from, date_to):
        """
        Получить выручку за период через функцию БД fn_revenue_between
        
        Args:
            date_from: начало периода
            date_to: конец периода
        
        Returns:
            list: список словарей с данными о выручке
        """
        with connection.cursor() as cursor:
            cursor.callproc('fn_revenue_between', [date_from, date_to])
            results = []
            for row in cursor.fetchall():
                results.append({
                    'month_date': row[0],
                    'revenue': row[1]
                })
        
        return results
    
    @staticmethod
    def get_dashboard_stats():
        """
        Получить общую статистику для дашборда.
        Считаем по таблице orders (только статус 'Completed'), как в представлениях аналитики.
        """
        cache_key = 'dashboard_stats'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0)
                FROM orders
                WHERE status = 'Completed'
            """)
            total_revenue = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*)
                FROM orders
                WHERE status = 'Completed'
            """)
            total_orders = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*)
                FROM users
            """)
            active_users = cursor.fetchone()[0]

        top_products = AnalyticsService.get_top_products(limit=5)

        stats = {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'active_users': active_users,
            'top_products': top_products,
        }

        cache.set(cache_key, stats, 60)
        return stats
    
    @staticmethod
    def invalidate_cache():
        cache_keys = [
            'dashboard_stats',
            'sales_by_product_*',
            'monthly_sales_*',
            'top_products_*',
        ]
        for limit in [5, 10, 20, 50]:
            cache.delete(f'top_products_{limit}')
        for year in range(2020, 2030):
            cache.delete(f'monthly_sales_{year}')
        cache.delete('dashboard_stats')

