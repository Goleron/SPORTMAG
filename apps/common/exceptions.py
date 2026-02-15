"""
Кастомные исключения для обработки бизнес-логики
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class InsufficientStockError(APIException):
    """Недостаточно товара на складе"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Недостаточно товара на складе'
    default_code = 'insufficient_stock'


class EmptyCartError(APIException):
    """Корзина пуста"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Корзина пуста'
    default_code = 'empty_cart'


class InvalidPaymentAmountError(APIException):
    """Неверная сумма платежа"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Сумма платежа не соответствует сумме заказа'
    default_code = 'invalid_payment_amount'


class ProductNotFoundError(APIException):
    """Товар не найден"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Товар не найден'
    default_code = 'product_not_found'


class OrderNotFoundError(APIException):
    """Заказ не найден"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Заказ не найден'
    default_code = 'order_not_found'

