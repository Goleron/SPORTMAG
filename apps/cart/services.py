"""
Сервис корзины: получение, добавление, обновление, удаление, валидация.
"""
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import CartItem
from apps.catalog.models import Product
from apps.catalog.services import ProductService

User = get_user_model()


class CartService:
    """Сервис для работы с корзиной"""
    
    @staticmethod
    def get_cart(user):
        """
        Получить корзину пользователя
        
        Args:
            user: объект пользователя
        
        Returns:
            QuerySet элементов корзины
        """
        return CartItem.objects.filter(user=user).select_related('product', 'product__category')
    
    @staticmethod
    def get_cart_total(user):
        """
        Получить общую стоимость корзины
        
        Args:
            user: объект пользователя
        
        Returns:
            dict: {'total_items': int, 'total_price': Decimal}
        """
        cart_items = CartService.get_cart(user)
        total_items = sum(item.quantity for item in cart_items)
        total_price = sum(item.get_total_price() for item in cart_items)
        
        return {
            'total_items': total_items,
            'total_price': total_price
        }
    
    @staticmethod
    @transaction.atomic
    def add_to_cart(user, product_id, quantity=1):
        """
        Добавить товар в корзину
        
        Args:
            user: объект пользователя
            product_id: ID товара
            quantity: количество
        
        Returns:
            CartItem: созданный или обновленный элемент корзины
        
        Raises:
            ValueError: если товар недоступен или недостаточно на складе
        """
        is_available, product = ProductService.check_availability(product_id, quantity)
        if not is_available:
            if product:
                raise ValueError(
                    f'Недостаточно товара на складе. Доступно: {product.stock_quantity}, '
                    f'запрошено: {quantity}'
                )
            else:
                raise ValueError('Товар не найден или недоступен')
        cart_item, created = CartItem.objects.get_or_create(
            user=user,
            product_id=product_id,
            defaults={'quantity': quantity}
        )
        if not created:
            new_quantity = cart_item.quantity + quantity
            if product.stock_quantity < new_quantity:
                raise ValueError(
                    f'Недостаточно товара на складе. В корзине: {cart_item.quantity}, '
                    f'добавляется: {quantity}, доступно: {product.stock_quantity}'
                )
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=['quantity', 'updated_at'])
        
        return cart_item
    
    @staticmethod
    @transaction.atomic
    def update_cart_item(user, item_id, quantity):
        """
        Обновить количество товара в корзине
        
        Args:
            user: объект пользователя
            item_id: ID элемента корзины
            quantity: новое количество
        
        Returns:
            CartItem: обновленный элемент корзины
        
        Raises:
            ValueError: если товар недоступен или недостаточно на складе
        """
        try:
            cart_item = CartItem.objects.select_related('product').get(
                id=item_id,
                user=user
            )
        except CartItem.DoesNotExist:
            raise ValueError('Элемент корзины не найден')
        
        if quantity < 1:
            raise ValueError('Количество должно быть больше 0')
        if cart_item.product.stock_quantity < quantity:
            raise ValueError(
                f'Недостаточно товара на складе. Доступно: {cart_item.product.stock_quantity}, '
                f'запрошено: {quantity}'
            )
        
        cart_item.quantity = quantity
        cart_item.save(update_fields=['quantity', 'updated_at'])
        
        return cart_item
    
    @staticmethod
    def remove_from_cart(user, item_id):
        """
        Удалить товар из корзины
        
        Args:
            user: объект пользователя
            item_id: ID элемента корзины
        
        Returns:
            bool: True если удалено успешно
        
        Raises:
            ValueError: если элемент не найден
        """
        try:
            cart_item = CartItem.objects.get(id=item_id, user=user)
            cart_item.delete()
            return True
        except CartItem.DoesNotExist:
            raise ValueError('Элемент корзины не найден')
    
    @staticmethod
    def clear_cart(user):
        """
        Очистить корзину пользователя
        
        Args:
            user: объект пользователя
        
        Returns:
            int: количество удаленных элементов
        """
        count, _ = CartItem.objects.filter(user=user).delete()
        return count
    
    @staticmethod
    def validate_cart(user):
        """
        Валидация корзины перед созданием заказа
        
        Проверяет:
        - наличие товаров в корзине
        - доступность всех товаров
        - достаточность остатков на складе
        
        Args:
            user: объект пользователя
        
        Returns:
            tuple: (is_valid, errors_list)
        """
        cart_items = CartService.get_cart(user)
        errors = []
        
        if not cart_items.exists():
            errors.append('Корзина пуста')
            return False, errors
        
        for item in cart_items:
            if not item.product.is_available:
                errors.append(f'Товар "{item.product.name}" недоступен')
            elif item.product.stock_quantity < item.quantity:
                errors.append(
                    f'Недостаточно товара "{item.product.name}" на складе. '
                    f'В корзине: {item.quantity}, доступно: {item.product.stock_quantity}'
                )
        
        return len(errors) == 0, errors

