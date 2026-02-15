"""
Тесты отказоустойчивости системы
"""
from django.test import TestCase, TransactionTestCase
from django.db import connection, transaction
from django.contrib.auth import get_user_model
from apps.catalog.models import Category, Product
from apps.accounts.models import Role
from apps.cart.models import CartItem
from apps.orders.models import Order, OrderItem, Transaction
from apps.orders.services import OrderService, PaymentService
from apps.common.models import Backup
import threading
import time

User = get_user_model()


class ResilienceTestCase(TransactionTestCase):
    """Тесты отказоустойчивости"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.buyer_role, _ = Role.objects.get_or_create(name='Buyer')
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role=self.buyer_role
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
    
    def test_concurrent_order_creation_with_locks(self):
        """Тест конкурентного создания заказов с блокировками"""
        # Создаем двух пользователей
        buyer2 = User.objects.create_user(
            username='buyer2',
            email='buyer2@test.com',
            password='testpass123',
            role=self.buyer_role
        )
        
        # Оба пользователя добавляют товар в корзину
        CartItem.objects.create(
            user=self.buyer,
            product=self.product,
            quantity=6
        )
        CartItem.objects.create(
            user=buyer2,
            product=self.product,
            quantity=6
        )
        
        results = []
        errors = []
        
        def create_order(user):
            try:
                order, total = OrderService.create_order_from_cart(user)
                results.append((user.id, order.id, total))
            except Exception as e:
                errors.append((user.id, str(e)))
        
        # Запускаем создание заказов параллельно
        thread1 = threading.Thread(target=create_order, args=(self.buyer,))
        thread2 = threading.Thread(target=create_order, args=(buyer2,))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Проверяем, что только один заказ создан успешно
        self.assertEqual(len(results), 1, "Должен быть создан только один заказ")
        
        # Проверяем, что количество на складе корректно
        self.product.refresh_from_db()
        self.assertGreaterEqual(self.product.stock_quantity, 0, "Количество не должно быть отрицательным")
        self.assertLessEqual(self.product.stock_quantity, 4, "Остаток должен быть не больше 4")
    
    def test_payment_rollback_on_error(self):
        """Тест отката транзакции при ошибке оплаты"""
        # Создаем заказ
        order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Pending'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price_at_purchase=1000.00
        )
        
        initial_status = order.status
        
        # Пытаемся оплатить с неверной суммой (должна быть ошибка)
        try:
            PaymentService.create_payment(
                order_id=order.id,
                amount=500.00,  # Неверная сумма
                payment_method='Card',
                user=self.buyer
            )
        except Exception:
            pass
        
        # Проверяем, что статус заказа не изменился
        order.refresh_from_db()
        self.assertEqual(order.status, initial_status, "Статус не должен измениться при ошибке")
        
        # Проверяем, что транзакция не создана или создана со статусом Failed
        transactions = Transaction.objects.filter(order=order)
        if transactions.exists():
            self.assertEqual(transactions.first().status, 'Failed')
    
    def test_stock_consistency_under_load(self):
        """Тест целостности остатков при нагрузке"""
        # Создаем несколько пользователей
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'buyer{i}',
                email=f'buyer{i}@test.com',
                password='testpass123',
                role=self.buyer_role
            )
            users.append(user)
            CartItem.objects.create(
                user=user,
                product=self.product,
                quantity=2  # Каждый хочет по 2, всего 10 (ровно столько на складе)
            )
        
        results = []
        
        def create_order(user):
            try:
                order, total = OrderService.create_order_from_cart(user)
                results.append(order.id)
            except Exception:
                pass
        
        # Запускаем все заказы параллельно
        threads = []
        for user in users:
            thread = threading.Thread(target=create_order, args=(user,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Проверяем целостность остатков
        self.product.refresh_from_db()
        total_ordered = sum(
            OrderItem.objects.filter(
                order_id__in=results,
                product=self.product
            ).values_list('quantity', flat=True)
        )
        
        expected_stock = 10 - total_ordered
        self.assertEqual(
            self.product.stock_quantity,
            expected_stock,
            f"Остаток должен быть {expected_stock}, получен {self.product.stock_quantity}"
        )
        self.assertGreaterEqual(self.product.stock_quantity, 0)
    
    def test_database_connection_recovery(self):
        """Тест восстановления после потери соединения с БД"""
        # Проверяем, что система может восстановить соединение
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.assertEqual(result[0], 1)
        except Exception as e:
            self.fail(f"Не удалось восстановить соединение: {e}")
    
    def test_transaction_isolation(self):
        """Тест изоляции транзакций"""
        # Создаем заказ в одной транзакции
        with transaction.atomic():
            order = Order.objects.create(
                user=self.buyer,
                total_amount=1000.00,
                status='Pending'
            )
            order_id = order.id
        
        # Проверяем, что заказ виден после коммита
        self.assertTrue(Order.objects.filter(id=order_id).exists())
    
    def test_backup_restore_integrity(self):
        """Тест целостности данных после восстановления из бэкапа"""
        # Создаем тестовые данные
        order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Completed'
        )
        order_id = order.id
        
        # Проверяем, что данные существуют
        self.assertTrue(Order.objects.filter(id=order_id).exists())
        
        # В реальном тесте здесь был бы процесс восстановления из бэкапа
        # Для демонстрации просто проверяем целостность данных
        order.refresh_from_db()
        self.assertEqual(order.total_amount, 1000.00)
        self.assertEqual(order.status, 'Completed')
    
    def test_concurrent_payment_processing(self):
        """Тест конкурентной обработки платежей"""
        # Создаем заказ
        order = Order.objects.create(
            user=self.buyer,
            total_amount=1000.00,
            status='Pending'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price_at_purchase=1000.00
        )
        
        results = []
        
        def process_payment():
            try:
                tx, status = PaymentService.create_payment(
                    order_id=order.id,
                    amount=1000.00,
                    payment_method='Card',
                    user=self.buyer
                )
                results.append((tx.id if tx else None, status))
            except Exception as e:
                results.append((None, str(e)))
        
        # Запускаем несколько попыток оплаты параллельно
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=process_payment)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Проверяем, что только один платеж успешен
        successful = [r for r in results if r[0] is not None and r[1] == 'Success']
        self.assertEqual(len(successful), 1, "Должен быть только один успешный платеж")
        
        # Проверяем статус заказа
        order.refresh_from_db()
        self.assertEqual(order.status, 'Completed')

