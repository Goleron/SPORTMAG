"""
Тесты безопасности для работы с данными карт
"""
from django.test import TestCase
from apps.common.card_utils import (
    mask_card_number, get_last_four_digits, 
    validate_luhn_algorithm, detect_card_type, sanitize_card_data
)


class CardSecurityTestCase(TestCase):
    """Тесты безопасности работы с картами"""
    
    def test_mask_card_number_visa(self):
        """Тест маскирования номера Visa карты"""
        card = "4111111111111111"
        masked = mask_card_number(card)
        self.assertEqual(masked, "**** **** **** 1111")
        self.assertNotIn("4111", masked)
    
    def test_mask_card_number_amex(self):
        """Тест маскирования номера Amex карты"""
        card = "378282246310005"
        masked = mask_card_number(card)
        self.assertIn("0005", masked)
        self.assertNotIn("3782", masked)
    
    def test_get_last_four_digits(self):
        """Тест получения последних 4 цифр"""
        card = "4111111111111111"
        last_four = get_last_four_digits(card)
        self.assertEqual(last_four, "1111")
    
    def test_validate_luhn_algorithm_valid(self):
        """Тест валидации по алгоритму Луна - валидный номер"""
        # Валидный номер Visa (тестовый)
        valid_cards = [
            "4111111111111111",  # Visa test
            "5555555555554444",  # MasterCard test
            "378282246310005",   # Amex test
        ]
        
        for card in valid_cards:
            with self.subTest(card=card):
                self.assertTrue(validate_luhn_algorithm(card), f"Card {card} should be valid")
    
    def test_validate_luhn_algorithm_invalid(self):
        """Тест валидации по алгоритму Луна - невалидный номер"""
        invalid_cards = [
            "4111111111111112",  # Неправильная контрольная сумма
            "1234567890123456",  # Случайный номер
            "0000000000000000",  # Все нули
        ]
        
        for card in invalid_cards:
            with self.subTest(card=card):
                self.assertFalse(validate_luhn_algorithm(card), f"Card {card} should be invalid")
    
    def test_detect_card_type_visa(self):
        """Тест определения типа карты - Visa"""
        visa_cards = ["4111111111111111", "4012888888881881"]
        for card in visa_cards:
            with self.subTest(card=card):
                self.assertEqual(detect_card_type(card), "Visa")
    
    def test_detect_card_type_mastercard(self):
        """Тест определения типа карты - MasterCard"""
        mc_cards = ["5555555555554444", "5105105105105100"]
        for card in mc_cards:
            with self.subTest(card=card):
                self.assertEqual(detect_card_type(card), "MasterCard")
    
    def test_detect_card_type_amex(self):
        """Тест определения типа карты - American Express"""
        amex_cards = ["378282246310005", "371449635398431"]
        for card in amex_cards:
            with self.subTest(card=card):
                self.assertEqual(detect_card_type(card), "American Express")
    
    def test_sanitize_card_data(self):
        """Тест очистки данных карты для логирования"""
        card_number = "4111111111111111"
        card_cvv = "123"
        card_expiry = "12/2025"
        
        sanitized = sanitize_card_data(card_number, card_cvv, card_expiry)
        
        # Проверяем, что полные данные не присутствуют
        self.assertNotIn("4111111111111111", str(sanitized))
        self.assertNotIn("123", str(sanitized))
        
        # Проверяем, что есть замаскированные данные
        self.assertIn("masked", str(sanitized).lower() or "****" in str(sanitized))
        self.assertEqual(sanitized.get('card_cvv'), '***')
        self.assertIn('last_four', sanitized)
    
    def test_sanitize_card_data_no_cvv(self):
        """Тест очистки данных карты без CVV"""
        card_number = "4111111111111111"
        sanitized = sanitize_card_data(card_number=card_number)
        
        self.assertIn('card_number', sanitized)
        self.assertIn('last_four', sanitized)
        self.assertNotIn('card_cvv', sanitized)
    
    def test_mask_card_number_with_spaces(self):
        """Тест маскирования номера карты с пробелами"""
        card = "4111 1111 1111 1111"
        masked = mask_card_number(card)
        self.assertIn("1111", masked)
        self.assertNotIn("4111", masked)
    
    def test_mask_card_number_short(self):
        """Тест маскирования короткого номера"""
        card = "123"
        masked = mask_card_number(card)
        self.assertEqual(len(masked), 3)
        self.assertEqual(masked, "***")

