"""
Сервисный слой для работы с заказами
"""
import logging
from decimal import Decimal
from django.db import connection, transaction
from django.contrib.auth import get_user_model
from .models import Order, OrderItem, Transaction
from apps.catalog.models import Product
from apps.cart.services import CartService
from ..common.utils import set_current_user_id, set_current_role
from ..common.models import Log

logger = logging.getLogger(__name__)
User = get_user_model()


def _procedure_exists(procname):
    """Проверяет наличие хранимой процедуры/функции в БД (для fallback в тестах)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT 1 FROM pg_proc WHERE proname = %s',
                [procname]
            )
            return cursor.fetchone() is not None
    except Exception:
        return False


def _create_order_from_cart_python(user):
    """
    Резервная реализация создания заказа из корзины на Python.
    Используется, если в БД нет хранимой процедуры create_order_from_cart (например, в тестах).
    """
    cart_items = list(CartService.get_cart(user))
    if not cart_items:
        raise ValueError('Корзина пуста')
    total_amount = Decimal('0')
    order = Order.objects.create(user=user, total_amount=0, status='Pending')
    try:
        for item in cart_items:
            product = item.product
            if product.stock_quantity < item.quantity:
                raise ValueError(
                    f'Недостаточно товара "{product.name}" на складе. '
                    f'В корзине: {item.quantity}, доступно: {product.stock_quantity}'
                )
            price = product.price
            subtotal = price * item.quantity
            total_amount += subtotal
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                price_at_purchase=price
            )
            Product.objects.filter(pk=product.pk).update(
                stock_quantity=product.stock_quantity - item.quantity
            )
        order.total_amount = total_amount
        order.save(update_fields=['total_amount'])
        CartItem = __import__('apps.cart.models', fromlist=['CartItem']).CartItem
        CartItem.objects.filter(user=user).delete()
        return order, total_amount
    except Exception:
        order.delete()
        raise


class OrderService:
    """Сервис для работы с заказами"""
    
    @staticmethod
    @transaction.atomic
    def create_order_from_cart(user):
        """
        Создание заказа из корзины через функцию БД create_order_from_cart
        (при отсутствии процедуры в БД — резервная реализация на Python).
        
        Args:
            user: объект пользователя
        
        Returns:
            tuple: (order, total_amount) — order может быть объектом Order
        
        Raises:
            ValueError: если корзина пуста или недостаточно товаров
        """
        # Валидация корзины
        is_valid, errors = CartService.validate_cart(user)
        if not is_valid:
            raise ValueError('; '.join(errors))
        
        # Устанавливаем контекст пользователя для триггеров БД
        set_current_user_id(user.id)
        if user.role:
            set_current_role(user.role.name)
        
        # Если процедуры нет в БД (например, тестовая БД) — используем Python-реализацию
        if not _procedure_exists('create_order_from_cart'):
            order, total_amount = _create_order_from_cart_python(user)
            Log.objects.create(
                level='INFO',
                message=f'Order #{order.id} created for user {user.username} (Python fallback)',
                user_id=user.id,
                meta={'order_id': order.id, 'total_amount': str(total_amount), 'action': 'order_created'}
            )
            return order, total_amount
        
        try:
            with connection.cursor() as cursor:
                cursor.callproc('create_order_from_cart', [user.id])
                result = cursor.fetchone()
                if result:
                    order_id = result[0]
                    total_amount = result[1]
                    Log.objects.create(
                        level='INFO',
                        message=f'Order #{order_id} created for user {user.username}',
                        user_id=user.id,
                        meta={
                            'order_id': order_id,
                            'total_amount': str(total_amount),
                            'action': 'order_created'
                        }
                    )
                    logger.info(f'Order #{order_id} created: user={user.id}, total={total_amount}')
                    order = Order.objects.select_related('user').prefetch_related('items__product').get(id=order_id)
                    return order, total_amount
                raise ValueError('Ошибка при создании заказа')
        except Exception as e:
            Log.objects.create(
                level='ERROR',
                message=f'Failed to create order for user {user.username}: {str(e)}',
                user_id=user.id,
                meta={'action': 'order_creation_failed', 'error': str(e)}
            )
            logger.error(f'Order creation failed: user={user.id}, error={str(e)}')
            raise
    
    @staticmethod
    def get_user_orders(user, status=None):
        """
        Получить заказы пользователя
        
        Args:
            user: объект пользователя
            status: фильтр по статусу (опционально)
        
        Returns:
            QuerySet заказов
        """
        queryset = Order.objects.filter(user=user).select_related('user').prefetch_related(
            'items__product',
            'transactions'
        ).order_by('-order_date')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    @staticmethod
    def get_order_by_id(order_id, user=None):
        """
        Получить заказ по ID
        
        Args:
            order_id: ID заказа
            user: пользователь (для проверки прав доступа)
        
        Returns:
            Order или None
        """
        try:
            queryset = Order.objects.select_related('user').prefetch_related(
                'items__product',
                'transactions'
            )
            
            if user:
                # Если указан пользователь, проверяем права доступа
                if user.role.name == 'Admin':
                    # Администратор видит все заказы
                    return queryset.get(id=order_id)
                else:
                    # Обычный пользователь видит только свои заказы
                    return queryset.get(id=order_id, user=user)
            else:
                return queryset.get(id=order_id)
        except Order.DoesNotExist:
            return None


class PaymentService:
    """Сервис для работы с платежами"""
    
    @staticmethod
    @transaction.atomic
    def create_payment(order_id, amount, payment_method, user=None):
        """
        Создание платежа через функцию БД create_payment
        
        Args:
            order_id: ID заказа
            amount: сумма платежа
            payment_method: способ оплаты
            user: пользователь (для установки контекста)
        
        Returns:
            tuple: (transaction_id, status)
        
        Raises:
            ValueError: если заказ не найден или сумма не совпадает
        """
        # Устанавливаем контекст пользователя
        if user:
            set_current_user_id(user.id)
            if user.role:
                set_current_role(user.role.name)
        
        # Валидация суммы платежа
        try:
            order = Order.objects.get(id=order_id)
            if float(amount) != float(order.total_amount):
                error_msg = f'Payment amount {amount} does not match order total {order.total_amount}'
                Log.objects.create(
                    level='WARNING',
                    message=f'Payment validation failed for order #{order_id}: {error_msg}',
                    user_id=user.id if user else None,
                    meta={
                        'order_id': order_id,
                        'requested_amount': str(amount),
                        'order_total': str(order.total_amount),
                        'action': 'payment_validation_failed'
                    }
                )
                raise ValueError(error_msg)
        except Order.DoesNotExist:
            raise ValueError(f'Order {order_id} not found')
        
        # Если процедуры нет в БД — резервная реализация на Python
        if not _procedure_exists('create_payment'):
            order = Order.objects.get(id=order_id)
            tx = Transaction.objects.create(
                order=order,
                amount=amount,
                payment_method=payment_method,
                status='Success'
            )
            order.status = 'Completed'
            order.save(update_fields=['status'])
            Log.objects.create(
                level='INFO',
                message=f'Payment transaction #{tx.id} for order #{order_id}: Success (Python fallback)',
                user_id=user.id if user else None,
                meta={'transaction_id': tx.id, 'order_id': order_id, 'action': 'payment_processed'}
            )
            try:
                from apps.analytics.services import AnalyticsService
                AnalyticsService.invalidate_cache()
            except Exception:
                pass
            return tx, 'Success'

        try:
            with connection.cursor() as cursor:
                cursor.callproc('create_payment', [order_id, amount, payment_method])
                result = cursor.fetchone()
                if result:
                    transaction_id = result[0]
                    status = result[1]
                    log_level = 'INFO' if status == 'Success' else 'ERROR'
                    Log.objects.create(
                        level=log_level,
                        message=f'Payment transaction #{transaction_id} for order #{order_id}: {status}',
                        user_id=user.id if user else None,
                        meta={
                            'transaction_id': transaction_id,
                            'order_id': order_id,
                            'amount': str(amount),
                            'payment_method': payment_method,
                            'status': status,
                            'action': 'payment_processed'
                        }
                    )
                    logger.info(f'Payment processed: tx_id={transaction_id}, order_id={order_id}, amount={amount}, status={status}')
                    if status == 'Success':
                        from apps.analytics.services import AnalyticsService
                        AnalyticsService.invalidate_cache()
                    if transaction_id:
                        transaction_obj = Transaction.objects.select_related('order').get(id=transaction_id)
                        return transaction_obj, status
                    return None, status
                raise ValueError('Ошибка при создании платежа')
        except Exception as e:
            # Логируем ошибку платежа
            Log.objects.create(
                level='ERROR',
                message=f'Payment processing failed for order #{order_id}: {str(e)}',
                user_id=user.id if user else None,
                meta={
                    'order_id': order_id,
                    'amount': str(amount),
                    'payment_method': payment_method,
                    'action': 'payment_failed',
                    'error': str(e)
                }
            )
            logger.error(f'Payment failed: order_id={order_id}, error={str(e)}')
            raise
    
    @staticmethod
    @transaction.atomic
    def refund_transaction(transaction_id, user=None):
        """
        Возврат транзакции через функцию БД refund_transaction
        
        Args:
            transaction_id: ID транзакции
            user: пользователь (для установки контекста)
        
        Returns:
            str: сообщение о результате
        
        Raises:
            ValueError: если транзакция не найдена или не может быть возвращена
        """
        # Устанавливаем контекст пользователя
        if user:
            set_current_user_id(user.id)
            if user.role:
                set_current_role(user.role.name)
        
        # Вызываем функцию БД
        try:
            with connection.cursor() as cursor:
                cursor.callproc('refund_transaction', [transaction_id])
                result = cursor.fetchone()
                
                if result:
                    message = result[0]
                    
                    # Логируем возврат транзакции
                    Log.objects.create(
                        level='INFO',
                        message=f'Transaction #{transaction_id} refunded: {message}',
                        user_id=user.id if user else None,
                        meta={
                            'transaction_id': transaction_id,
                            'action': 'transaction_refunded',
                            'result': message
                        }
                    )
                    
                    logger.info(f'Transaction refunded: tx_id={transaction_id}, result={message}')
                    from apps.analytics.services import AnalyticsService
                    AnalyticsService.invalidate_cache()
                    return message
                else:
                    raise ValueError('Ошибка при возврате транзакции')
        except Exception as e:
            # Логируем ошибку возврата
            Log.objects.create(
                level='ERROR',
                message=f'Refund failed for transaction #{transaction_id}: {str(e)}',
                user_id=user.id if user else None,
                meta={
                    'transaction_id': transaction_id,
                    'action': 'refund_failed',
                    'error': str(e)
                }
            )
            logger.error(f'Refund failed: tx_id={transaction_id}, error={str(e)}')
            raise

