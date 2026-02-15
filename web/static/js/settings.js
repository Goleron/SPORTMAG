/**
 * Применение настроек пользователя в интерфейсе
 */

(function() {
    'use strict';
    
    // Получаем настройки из глобальной переменной, мета-тега или localStorage
    function getSettings() {
        // Сначала проверяем глобальную переменную из сервера
        if (window.userSettingsFromServer) {
            return window.userSettingsFromServer;
        }
        
        // Затем проверяем мета-тег
        const metaSettings = document.querySelector('meta[name="user-settings"]');
        if (metaSettings) {
            try {
                const parsed = JSON.parse(metaSettings.content);
                if (parsed && typeof parsed === 'object') {
                    return parsed;
                }
            } catch (e) {
                console.error('Ошибка парсинга настроек из мета-тега:', e);
            }
        }
        
        // Пробуем получить из localStorage
        const saved = localStorage.getItem('user_settings');
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch (e) {
                console.error('Ошибка парсинга настроек из localStorage:', e);
            }
        }
        
        return {
            date_format: 'DD.MM.YYYY',
            number_format: 'ru',
            page_size: 20
        };
    }
    
    // Форматирование даты
    function formatDate(date, format) {
        if (!date) return '';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return date;
        
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year = d.getFullYear();
        const monthNames = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
        
        switch(format) {
            case 'DD.MM.YYYY':
                return `${day}.${month}.${year}`;
            case 'YYYY-MM-DD':
                return `${year}-${month}-${day}`;
            case 'MM/DD/YYYY':
                return `${month}/${day}/${year}`;
            case 'DD MMM YYYY':
                return `${day} ${monthNames[d.getMonth()]} ${year}`;
            default:
                return `${day}.${month}.${year}`;
        }
    }
    
    // Форматирование чисел
    function formatNumber(num, format) {
        if (num === null || num === undefined) return '';
        
        const numStr = String(num);
        const parts = numStr.split('.');
        const integerPart = parts[0];
        const decimalPart = parts[1] || '';
        
        // Добавляем разделители тысяч
        let formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
        
        switch(format) {
            case 'ru':
                return decimalPart ? `${formattedInteger},${decimalPart}` : formattedInteger;
            case 'en':
                formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
                return decimalPart ? `${formattedInteger}.${decimalPart}` : formattedInteger;
            case 'space':
                return decimalPart ? `${formattedInteger}.${decimalPart}` : formattedInteger;
            default:
                return decimalPart ? `${formattedInteger},${decimalPart}` : formattedInteger;
        }
    }
    
    // Применение форматирования ко всем датам на странице
    function applyDateFormat(format) {
        document.querySelectorAll('[data-date]').forEach(el => {
            const dateValue = el.getAttribute('data-date');
            if (dateValue) {
                el.textContent = formatDate(dateValue, format);
            }
        });
    }
    
    // Применение форматирования ко всем числам на странице
    function applyNumberFormat(format) {
        document.querySelectorAll('[data-number]').forEach(el => {
            const numValue = el.getAttribute('data-number');
            if (numValue) {
                el.textContent = formatNumber(parseFloat(numValue), format);
            }
        });
    }
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', function() {
        const settings = getSettings();
        
        // Применяем форматирование дат и чисел
        applyDateFormat(settings.date_format || 'DD.MM.YYYY');
        applyNumberFormat(settings.number_format || 'ru');
        
        // Сохраняем настройки в глобальную область для использования в других скриптах
        window.userSettings = settings;
        window.formatDate = formatDate;
        window.formatNumber = formatNumber;
    });
    
})();

