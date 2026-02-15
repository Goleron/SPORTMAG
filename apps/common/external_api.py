"""
Модуль для работы с внешними API
"""
import requests
import logging
from django.conf import settings
from django.core.cache import cache
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class ExchangeRateAPI:
    """
    Клиент для работы с API курсов валют
    Использует бесплатный API exchangerate-api.com
    """
    
    BASE_URL = "https://api.exchangerate-api.com/v4"
    CACHE_TIMEOUT = 3600  # 1 час
    
    def __init__(self):
        self.api_key = getattr(settings, 'EXCHANGE_RATE_API_KEY', None)
        # Если есть API ключ, используем его, иначе бесплатный endpoint
        if self.api_key:
            self.base_url = f"{self.BASE_URL}/latest"
        else:
            # Бесплатный endpoint без ключа (ограниченный)
            self.base_url = f"{self.BASE_URL}/latest/USD"
    
    def get_exchange_rates(self, base_currency: str = 'RUB') -> Optional[Dict[str, float]]:
        """
        Получить курсы валют относительно базовой валюты
        
        Args:
            base_currency: Базовая валюта (по умолчанию RUB)
        
        Returns:
            Словарь с курсами валют или None при ошибке
        """
        cache_key = f'exchange_rates_{base_currency}'
        
        # Проверяем кэш
        cached_rates = cache.get(cache_key)
        if cached_rates:
            return cached_rates
        
        # Retry логика с экспоненциальной задержкой
        max_retries = 3
        retry_delays = [1, 2, 4]  # секунды
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                url = f"{self.BASE_URL}/latest/{base_currency}"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                
                # Успешный запрос, обрабатываем ответ
                data = response.json()
                
                # Валидация ответа
                if not isinstance(data, dict):
                    logger.error(f"Неверный формат ответа от API курсов валют")
                    return None
                
                rates = data.get('rates', {})
                
                if not rates:
                    logger.warning(f"Пустой ответ от API курсов валют для {base_currency}")
                    return None
                
                # Валидация курсов (должны быть положительными числами)
                validated_rates = {}
                for currency, rate in rates.items():
                    try:
                        rate_float = float(rate)
                        if rate_float > 0:
                            validated_rates[currency] = rate_float
                        else:
                            logger.warning(f"Некорректный курс для {currency}: {rate}")
                    except (ValueError, TypeError):
                        logger.warning(f"Неверный формат курса для {currency}: {rate}")
                
                if not validated_rates:
                    logger.error(f"Нет валидных курсов валют для {base_currency}")
                    return None
                
                # Сохраняем в кэш
                cache.set(cache_key, validated_rates, self.CACHE_TIMEOUT)
                
                logger.info(f"Получены курсы валют для {base_currency}: {len(validated_rates)} валют")
                return validated_rates
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    import time
                    delay = retry_delays[attempt]
                    logger.warning(f"Попытка {attempt + 1}/{max_retries} не удалась для {base_currency}, повтор через {delay}с: {e}")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Все {max_retries} попытки не удались для {base_currency}: {e}")
                    # Пробуем вернуть кэшированные данные
                    cached_rates = cache.get(cache_key)
                    if cached_rates:
                        logger.info(f"Используем кэшированные курсы валют для {base_currency}")
                        return cached_rates
                    return None
            except requests.exceptions.HTTPError as e:
                # HTTP ошибки не ретраим (4xx, 5xx)
                logger.error(f"HTTP ошибка при получении курсов валют: {e.response.status_code} - {e}")
                return None
            except ValueError as e:
                logger.error(f"Ошибка парсинга JSON ответа: {e}")
                return None
            except Exception as e:
                logger.error(f"Неожиданная ошибка при получении курсов валют: {e}", exc_info=True)
                return None
        
        # Если дошли сюда, все попытки не удались
        if last_exception:
            cached_rates = cache.get(cache_key)
            if cached_rates:
                logger.info(f"Используем кэшированные курсы валют для {base_currency} после ошибок")
                return cached_rates
        return None
    
    def convert_currency(self, amount: Decimal, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """
        Конвертировать сумму из одной валюты в другую
        
        Args:
            amount: Сумма для конвертации
            from_currency: Исходная валюта
            to_currency: Целевая валюта
        
        Returns:
            Конвертированная сумма или None при ошибке
        """
        # Валидация входных данных
        if amount < 0:
            logger.warning(f"Отрицательная сумма для конвертации: {amount}")
            return None
        
        if not from_currency or not to_currency:
            logger.warning(f"Пустые коды валют: from={from_currency}, to={to_currency}")
            return None
        
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        if from_currency == to_currency:
            return amount
        
        rates = self.get_exchange_rates(from_currency)
        if not rates:
            logger.warning(f"Не удалось получить курсы для {from_currency}")
            return None
        
        rate = rates.get(to_currency)
        if not rate:
            logger.warning(f"Курс для валюты {to_currency} не найден (доступны: {list(rates.keys())[:10]})")
            return None
        
        try:
            converted = amount * Decimal(str(rate))
            result = converted.quantize(Decimal('0.01'))
            
            # Проверка на разумность результата
            if result < 0:
                logger.warning(f"Отрицательный результат конвертации: {result}")
                return None
            
            logger.info(f"Конвертация: {amount} {from_currency} = {result} {to_currency} (курс: {rate})")
            return result
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при конвертации валюты: {e}")
            return None
    
    def get_available_currencies(self) -> list:
        """
        Получить список доступных валют
        
        Returns:
            Список кодов валют
        """
        rates = self.get_exchange_rates('USD')
        if rates:
            return list(rates.keys()) + ['USD']
        return ['USD', 'EUR', 'RUB', 'GBP', 'JPY', 'CNY']


class DeliveryAPI:
    """
    Клиент для работы с API расчета доставки
    Использует мок-сервис для демонстрации
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'DELIVERY_API_URL', 'https://api.example.com/delivery')
        self.api_key = getattr(settings, 'DELIVERY_API_KEY', None)
    
    def calculate_delivery_cost(
        self, 
        weight: float, 
        distance: float, 
        delivery_type: str = 'standard'
    ) -> Optional[Decimal]:
        """
        Рассчитать стоимость доставки
        
        Args:
            weight: Вес в кг
            distance: Расстояние в км
            delivery_type: Тип доставки (standard, express, overnight)
        
        Returns:
            Стоимость доставки или None при ошибке
        """
        # Мок-реализация для демонстрации
        # В реальном проекте здесь был бы запрос к внешнему API
        
        base_cost = Decimal('200.00')  # Базовая стоимость
        
        # Коэффициенты в зависимости от типа доставки
        multipliers = {
            'standard': Decimal('1.0'),
            'express': Decimal('1.5'),
            'overnight': Decimal('2.0'),
        }
        
        multiplier = multipliers.get(delivery_type, Decimal('1.0'))
        
        # Расчет на основе веса и расстояния
        weight_cost = Decimal(str(weight)) * Decimal('10.00')
        distance_cost = Decimal(str(distance)) * Decimal('5.00')
        
        total = (base_cost + weight_cost + distance_cost) * multiplier
        
        logger.info(f"Рассчитана стоимость доставки: {total} руб. (вес: {weight}кг, расстояние: {distance}км, тип: {delivery_type})")
        
        return total.quantize(Decimal('0.01'))
    
    def get_delivery_time(self, distance: float, delivery_type: str = 'standard') -> int:
        """
        Получить время доставки в днях
        
        Args:
            distance: Расстояние в км
            delivery_type: Тип доставки
        
        Returns:
            Время доставки в днях
        """
        # Мок-реализация
        base_days = {
            'standard': 5,
            'express': 2,
            'overnight': 1,
        }
        
        days = base_days.get(delivery_type, 5)
        
        # Увеличиваем время в зависимости от расстояния
        if distance > 1000:
            days += 2
        elif distance > 500:
            days += 1
        
        return days


# Singleton экземпляры
_exchange_rate_api = None
_delivery_api = None


def get_exchange_rate_api() -> ExchangeRateAPI:
    """Получить экземпляр ExchangeRateAPI"""
    global _exchange_rate_api
    if _exchange_rate_api is None:
        _exchange_rate_api = ExchangeRateAPI()
    return _exchange_rate_api


def get_delivery_api() -> DeliveryAPI:
    """Получить экземпляр DeliveryAPI"""
    global _delivery_api
    if _delivery_api is None:
        _delivery_api = DeliveryAPI()
    return _delivery_api

