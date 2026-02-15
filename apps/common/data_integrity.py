"""
Модуль для проверки целостности данных
"""
from django.db import connection
from django.core.exceptions import ValidationError
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataIntegrityChecker:
    """Класс для проверки целостности данных"""
    
    @staticmethod
    def check_orders_integrity() -> List[Dict[str, Any]]:
        """
        Проверка целостности заказов
        
        Returns:
            Список найденных проблем
        """
        issues = []
        
        with connection.cursor() as cursor:
            # Проверка 1: Заказы без позиций
            cursor.execute("""
                SELECT o.id, o.user_id, o.total_amount, o.status
                FROM shop.orders o
                LEFT JOIN shop.order_items oi ON o.id = oi.order_id
                WHERE oi.id IS NULL
            """)
            empty_orders = cursor.fetchall()
            if empty_orders:
                issues.append({
                    'type': 'empty_orders',
                    'message': f'Найдено {len(empty_orders)} заказов без позиций',
                    'count': len(empty_orders),
                    'details': [{'order_id': row[0], 'user_id': row[1]} for row in empty_orders[:10]]
                })
            
            # Проверка 2: Несоответствие суммы заказа сумме позиций
            cursor.execute("""
                SELECT o.id, o.total_amount, 
                       COALESCE(SUM(oi.quantity * oi.price_at_purchase), 0) as calculated_total
                FROM shop.orders o
                LEFT JOIN shop.order_items oi ON o.id = oi.order_id
                GROUP BY o.id, o.total_amount
                HAVING ABS(o.total_amount - COALESCE(SUM(oi.quantity * oi.price_at_purchase), 0)) > 0.01
            """)
            mismatched_orders = cursor.fetchall()
            if mismatched_orders:
                issues.append({
                    'type': 'amount_mismatch',
                    'message': f'Найдено {len(mismatched_orders)} заказов с несоответствием суммы',
                    'count': len(mismatched_orders),
                    'details': [
                        {
                            'order_id': row[0],
                            'order_total': float(row[1]),
                            'calculated_total': float(row[2])
                        } for row in mismatched_orders[:10]
                    ]
                })
            
            # Проверка 3: Транзакции без заказов (не должно быть, но проверим)
            cursor.execute("""
                SELECT t.id, t.order_id
                FROM shop.transactions t
                LEFT JOIN shop.orders o ON t.order_id = o.id
                WHERE o.id IS NULL
            """)
            orphan_transactions = cursor.fetchall()
            if orphan_transactions:
                issues.append({
                    'type': 'orphan_transactions',
                    'message': f'Найдено {len(orphan_transactions)} транзакций без заказов',
                    'count': len(orphan_transactions),
                    'details': [{'transaction_id': row[0], 'order_id': row[1]} for row in orphan_transactions[:10]]
                })
            
            # Проверка 4: Отрицательные остатки товаров
            cursor.execute("""
                SELECT id, name, sku, stock_quantity
                FROM shop.products
                WHERE stock_quantity < 0
            """)
            negative_stock = cursor.fetchall()
            if negative_stock:
                issues.append({
                    'type': 'negative_stock',
                    'message': f'Найдено {len(negative_stock)} товаров с отрицательным остатком',
                    'count': len(negative_stock),
                    'details': [
                        {
                            'product_id': row[0],
                            'name': row[1],
                            'sku': row[2],
                            'stock': row[3]
                        } for row in negative_stock[:10]
                    ]
                })
            
            # Проверка 5: Заказы с несуществующими пользователями
            cursor.execute("""
                SELECT o.id, o.user_id
                FROM shop.orders o
                LEFT JOIN shop.users u ON o.user_id = u.id
                WHERE u.id IS NULL
            """)
            invalid_users = cursor.fetchall()
            if invalid_users:
                issues.append({
                    'type': 'invalid_user_reference',
                    'message': f'Найдено {len(invalid_users)} заказов с несуществующими пользователями',
                    'count': len(invalid_users),
                    'details': [{'order_id': row[0], 'user_id': row[1]} for row in invalid_users[:10]]
                })
        
        return issues
    
    @staticmethod
    def check_cart_integrity() -> List[Dict[str, Any]]:
        """
        Проверка целостности корзины
        
        Returns:
            Список найденных проблем
        """
        issues = []
        
        with connection.cursor() as cursor:
            # Проверка: Товары в корзине с нулевым или отрицательным количеством
            cursor.execute("""
                SELECT ci.id, ci.user_id, ci.product_id, ci.quantity
                FROM shop.cart_items ci
                WHERE ci.quantity <= 0
            """)
            invalid_quantities = cursor.fetchall()
            if invalid_quantities:
                issues.append({
                    'type': 'invalid_cart_quantity',
                    'message': f'Найдено {len(invalid_quantities)} позиций в корзине с невалидным количеством',
                    'count': len(invalid_quantities),
                    'details': [
                        {
                            'cart_item_id': row[0],
                            'user_id': row[1],
                            'product_id': row[2],
                            'quantity': row[3]
                        } for row in invalid_quantities[:10]
                    ]
                })
            
            # Проверка: Товары в корзине, которых нет на складе
            cursor.execute("""
                SELECT ci.id, ci.user_id, ci.product_id, ci.quantity, p.stock_quantity, p.is_available
                FROM shop.cart_items ci
                JOIN shop.products p ON ci.product_id = p.id
                WHERE p.stock_quantity < ci.quantity OR p.is_available = FALSE
            """)
            unavailable_items = cursor.fetchall()
            if unavailable_items:
                issues.append({
                    'type': 'unavailable_cart_items',
                    'message': f'Найдено {len(unavailable_items)} позиций в корзине с недоступными товарами',
                    'count': len(unavailable_items),
                    'details': [
                        {
                            'cart_item_id': row[0],
                            'user_id': row[1],
                            'product_id': row[2],
                            'requested_quantity': row[3],
                            'available_stock': row[4],
                            'is_available': row[5]
                        } for row in unavailable_items[:10]
                    ]
                })
        
        return issues
    
    @staticmethod
    def run_all_checks() -> Dict[str, Any]:
        """
        Запуск всех проверок целостности
        
        Returns:
            Словарь с результатами проверок
        """
        logger.info("Запуск проверки целостности данных")
        
        orders_issues = DataIntegrityChecker.check_orders_integrity()
        cart_issues = DataIntegrityChecker.check_cart_integrity()
        
        all_issues = orders_issues + cart_issues
        total_issues = sum(issue['count'] for issue in all_issues)
        
        result = {
            'status': 'ok' if total_issues == 0 else 'issues_found',
            'total_issues': total_issues,
            'orders_issues': orders_issues,
            'cart_issues': cart_issues,
            'all_issues': all_issues
        }
        
        logger.info(f"Проверка целостности завершена: найдено {total_issues} проблем")
        
        return result

