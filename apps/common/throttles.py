"""
Кастомные throttle классы для ограничения частоты запросов
"""
from rest_framework.throttling import UserRateThrottle


class AdminRateThrottle(UserRateThrottle):
    """Throttle для администраторов"""
    scope = 'admin'


class OrderCreateRateThrottle(UserRateThrottle):
    """Throttle для создания заказов"""
    scope = 'order_create'


class PaymentRateThrottle(UserRateThrottle):
    """Throttle для операций оплаты"""
    scope = 'payment'


class ImportRateThrottle(UserRateThrottle):
    """Throttle для импорта данных"""
    scope = 'import'

