"""
Утилиты для работы с банковскими картами
"""
import re
from typing import Optional, Tuple


def mask_card_number(card_number: str) -> str:
    """
    Маскирование номера карты (показываем только последние 4 цифры)
    
    Args:
        card_number: Номер карты
    
    Returns:
        Замаскированный номер карты (например, **** **** **** 1234)
    """
    if not card_number:
        return ''
    
    # Удаляем все нецифровые символы
    cleaned = re.sub(r'\D', '', card_number)
    
    if len(cleaned) < 4:
        return '*' * len(cleaned)
    
    # Показываем только последние 4 цифры
    last_four = cleaned[-4:]
    
    # Форматируем как карта (группы по 4 цифры)
    if len(cleaned) == 16:
        return f"**** **** **** {last_four}"
    elif len(cleaned) == 15:
        return f"**** ****** *{last_four}"
    else:
        # Для других длин просто маскируем все кроме последних 4
        masked = '*' * (len(cleaned) - 4)
        return f"{masked}{last_four}"


def get_last_four_digits(card_number: str) -> str:
    """
    Получить последние 4 цифры номера карты
    
    Args:
        card_number: Номер карты
    
    Returns:
        Последние 4 цифры
    """
    if not card_number:
        return ''
    
    cleaned = re.sub(r'\D', '', card_number)
    return cleaned[-4:] if len(cleaned) >= 4 else cleaned


def validate_luhn_algorithm(card_number: str) -> bool:
    """
    Проверка номера карты по алгоритму Луна
    
    Args:
        card_number: Номер карты
    
    Returns:
        True если номер валиден, False иначе
    """
    if not card_number:
        return False
    
    # Удаляем все нецифровые символы
    cleaned = re.sub(r'\D', '', card_number)
    
    if len(cleaned) < 13 or len(cleaned) > 19:
        return False
    
    # Алгоритм Луна
    def luhn_check(card_num):
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_num)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10 == 0
    
    return luhn_check(cleaned)


def detect_card_type(card_number: str) -> Optional[str]:
    """
    Определение типа карты по номеру
    
    Args:
        card_number: Номер карты
    
    Returns:
        Тип карты (Visa, MasterCard, Amex, etc.) или None
    """
    if not card_number:
        return None
    
    cleaned = re.sub(r'\D', '', card_number)
    
    if not cleaned:
        return None
    
    # Visa: начинается с 4, длина 13 или 16
    if re.match(r'^4', cleaned) and len(cleaned) in [13, 16]:
        return 'Visa'
    
    # MasterCard: начинается с 51-55 или 2221-2720, длина 16
    if re.match(r'^(5[1-5]|2[2-7])', cleaned) and len(cleaned) == 16:
        if re.match(r'^5[1-5]', cleaned):
            return 'MasterCard'
        elif re.match(r'^2[2-7]', cleaned):
            return 'MasterCard'
    
    # American Express: начинается с 34 или 37, длина 15
    if re.match(r'^3[47]', cleaned) and len(cleaned) == 15:
        return 'American Express'
    
    # Discover: начинается с 6011, 65, или 644-649, длина 16
    if re.match(r'^(6011|65|64[4-9])', cleaned) and len(cleaned) == 16:
        return 'Discover'
    
    # JCB: начинается с 35, длина 16
    if re.match(r'^35', cleaned) and len(cleaned) == 16:
        return 'JCB'
    
    return 'Unknown'


def sanitize_card_data(card_number: Optional[str] = None, 
                      card_cvv: Optional[str] = None,
                      card_expiry: Optional[str] = None) -> dict:
    """
    Очистка данных карты для безопасного логирования
    Не логируем полные данные карты
    
    Args:
        card_number: Номер карты
        card_cvv: CVV код
        card_expiry: Срок действия
    
    Returns:
        Словарь с замаскированными данными
    """
    sanitized = {}
    
    if card_number:
        sanitized['card_number'] = mask_card_number(card_number)
        sanitized['card_type'] = detect_card_type(card_number)
        sanitized['last_four'] = get_last_four_digits(card_number)
    
    if card_cvv:
        sanitized['card_cvv'] = '***'  # Никогда не логируем CVV
    
    if card_expiry:
        # Логируем только месяц/год без полной даты
        sanitized['card_expiry'] = card_expiry[:7] if len(card_expiry) >= 7 else '**/****'
    
    return sanitized

