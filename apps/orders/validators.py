"""
Валидаторы для заказов и платежей
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_payment_amount(value):
    """
    Валидация суммы платежа
    
    Args:
        value: сумма платежа
    
    Raises:
        ValidationError: если сумма невалидна
    """
    if value <= 0:
        raise ValidationError(_('Сумма платежа должна быть больше нуля'))
    
    if value > Decimal('999999999999.99'):
        raise ValidationError(_('Сумма платежа слишком большая'))
    
    # Проверка на разумность (не более 10 миллионов)
    if value > Decimal('10000000'):
        raise ValidationError(_('Сумма платежа превышает максимально допустимую'))


def validate_order_amount(value):
    """
    Валидация суммы заказа
    
    Args:
        value: сумма заказа
    
    Raises:
        ValidationError: если сумма невалидна
    """
    if value < 0:
        raise ValidationError(_('Сумма заказа не может быть отрицательной'))
    
    if value == 0:
        raise ValidationError(_('Сумма заказа должна быть больше нуля'))
    
    if value > Decimal('999999999999.99'):
        raise ValidationError(_('Сумма заказа слишком большая'))


def validate_quantity(value):
    """
    Валидация количества товара
    
    Args:
        value: количество
    
    Raises:
        ValidationError: если количество невалидно
    """
    if value <= 0:
        raise ValidationError(_('Количество должно быть больше нуля'))
    
    if value > 10000:
        raise ValidationError(_('Количество слишком большое (максимум 10000)'))


def validate_price(value):
    """
    Валидация цены товара
    
    Args:
        value: цена
    
    Raises:
        ValidationError: если цена невалидна
    """
    if value < 0:
        raise ValidationError(_('Цена не может быть отрицательной'))
    
    if value > Decimal('9999999999.99'):
        raise ValidationError(_('Цена слишком большая'))


def validate_card_number(value):
    """
    Валидация номера карты (проверка формата и алгоритм Луна)
    
    Args:
        value: номер карты
    
    Raises:
        ValidationError: если номер карты невалиден
    """
    if not value:
        return
    
    # Удаляем пробелы и дефисы
    cleaned = value.replace(' ', '').replace('-', '')
    
    if not cleaned.isdigit():
        raise ValidationError(_('Номер карты должен содержать только цифры'))
    
    if len(cleaned) < 13 or len(cleaned) > 19:
        raise ValidationError(_('Номер карты должен содержать от 13 до 19 цифр'))
    
    # Проверка по алгоритму Луна
    from ..common.card_utils import validate_luhn_algorithm
    if not validate_luhn_algorithm(cleaned):
        raise ValidationError(_('Номер карты не прошел проверку по алгоритму Луна'))


def validate_card_expiry(value):
    """
    Валидация срока действия карты (формат MM/YYYY)
    
    Args:
        value: срок действия в формате MM/YYYY
    
    Raises:
        ValidationError: если формат невалиден
    """
    if not value:
        return
    
    try:
        parts = value.split('/')
        if len(parts) != 2:
            raise ValueError
        
        month = int(parts[0])
        year = int(parts[1])
        
        if month < 1 or month > 12:
            raise ValidationError(_('Месяц должен быть от 01 до 12'))
        
        if year < 2000 or year > 2099:
            raise ValidationError(_('Год должен быть от 2000 до 2099'))
        
    except (ValueError, IndexError):
        raise ValidationError(_('Неверный формат срока действия карты. Используйте MM/YYYY'))


def validate_cvv(value):
    """
    Валидация CVV кода
    
    Args:
        value: CVV код
    
    Raises:
        ValidationError: если CVV невалиден
    """
    if not value:
        return
    
    if not value.isdigit():
        raise ValidationError(_('CVV должен содержать только цифры'))
    
    if len(value) < 3 or len(value) > 4:
        raise ValidationError(_('CVV должен содержать 3 или 4 цифры'))

