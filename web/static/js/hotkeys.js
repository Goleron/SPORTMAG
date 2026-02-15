/**
 * Модуль горячих клавиш для веб-интерфейса
 * Реализует минимум 8 горячих клавиш для частых операций
 */

(function() {
    'use strict';
    
    const hotkeys = {
        // Список всех горячих клавиш
        keys: {
            // Ctrl+K или / - поиск по каталогу
            'search': {
                key: 'k',
                ctrl: true,
                alt: false,
                shift: false,
                action: function() {
                    const searchInput = document.querySelector('input[type="search"], input[name="search"], #search-input');
                    if (searchInput) {
                        searchInput.focus();
                        searchInput.select();
                    } else {
                        // Если на странице нет поля поиска, переходим на страницу каталога
                        window.location.href = '/catalog/';
                    }
                },
                description: 'Поиск по каталогу'
            },
            
            // Ctrl+C - открыть корзину
            'cart': {
                key: 'c',
                ctrl: true,
                alt: false,
                shift: false,
                action: function() {
                    window.location.href = '/cart/';
                },
                description: 'Открыть корзину'
            },
            
            // Ctrl+O - открыть заказы
            'orders': {
                key: 'o',
                ctrl: true,
                alt: false,
                shift: false,
                action: function() {
                    window.location.href = '/orders/';
                },
                description: 'Открыть заказы'
            },
            
            // Ctrl+A - открыть аналитику (для Admin/Analyst)
            'analytics': {
                key: 'a',
                ctrl: true,
                alt: false,
                shift: false,
                action: function() {
                    window.location.href = '/analytics/';
                },
                description: 'Открыть аналитику'
            },
            
            // Esc - закрыть модальные окна
            'close': {
                key: 'Escape',
                ctrl: false,
                alt: false,
                shift: false,
                action: function() {
                    // Закрываем все открытые модальные окна Bootstrap
                    const modals = document.querySelectorAll('.modal.show');
                    modals.forEach(modal => {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) {
                            bsModal.hide();
                        }
                    });
                    
                    // Закрываем все открытые dropdown меню
                    const dropdowns = document.querySelectorAll('.dropdown-menu.show');
                    dropdowns.forEach(dropdown => {
                        const bsDropdown = bootstrap.Dropdown.getInstance(dropdown.previousElementSibling);
                        if (bsDropdown) {
                            bsDropdown.hide();
                        }
                    });
                    
                    // Закрываем алерты
                    const alerts = document.querySelectorAll('.alert');
                    alerts.forEach(alert => {
                        const bsAlert = bootstrap.Alert.getInstance(alert);
                        if (bsAlert) {
                            bsAlert.close();
                        }
                    });
                },
                description: 'Закрыть модальные окна'
            },
            
            // Ctrl+S - сохранить (в формах редактирования)
            'save': {
                key: 's',
                ctrl: true,
                alt: false,
                shift: false,
                action: function(e) {
                    // Предотвращаем стандартное сохранение страницы
                    e.preventDefault();
                    
                    // Ищем форму на странице
                    const form = document.querySelector('form');
                    if (form && form.querySelector('button[type="submit"]')) {
                        form.querySelector('button[type="submit"]').click();
                    }
                },
                description: 'Сохранить форму'
            },
            
            // Ctrl+/ - показать справку по горячим клавишам
            'help': {
                key: '/',
                ctrl: true,
                alt: false,
                shift: false,
                action: function(e) {
                    e.preventDefault();
                    showHotkeysHelp();
                },
                description: 'Показать справку по горячим клавишам'
            },
            
            // Ctrl+P - экспорт/печать текущей страницы
            'export': {
                key: 'p',
                ctrl: true,
                alt: false,
                shift: false,
                action: function(e) {
                    e.preventDefault();
                    // Проверяем, есть ли кнопка экспорта на странице
                    const exportBtn = document.querySelector('[data-export], .export-btn, button[data-action="export"]');
                    if (exportBtn) {
                        exportBtn.click();
                    } else {
                        // Если нет кнопки экспорта, открываем диалог печати
                        window.print();
                    }
                },
                description: 'Экспорт/печать страницы'
            },
            
            // Дополнительные горячие клавиши
            
            // Ctrl+H - перейти на главную
            'home': {
                key: 'h',
                ctrl: true,
                alt: false,
                shift: false,
                action: function() {
                    window.location.href = '/';
                },
                description: 'Перейти на главную'
            },
            
            // Ctrl+, - открыть настройки
            'settings': {
                key: ',',
                ctrl: true,
                alt: false,
                shift: false,
                action: function() {
                    window.location.href = '/settings/';
                },
                description: 'Открыть настройки'
            }
        },
        
        // Обработчик событий клавиатуры
        handleKeyPress: function(e) {
            // Игнорируем, если пользователь вводит текст в поле ввода
            const tagName = e.target.tagName.toLowerCase();
            if (tagName === 'input' || tagName === 'textarea') {
                // Разрешаем только Esc и Ctrl+/
                if (e.key === 'Escape' || (e.ctrlKey && e.key === '/')) {
                    // Продолжаем обработку
                } else {
                    return;
                }
            }
            
            // Проверяем все зарегистрированные горячие клавиши
            for (const [name, config] of Object.entries(this.keys)) {
                if (this.matchesKey(e, config)) {
                    e.preventDefault();
                    config.action(e);
                    return;
                }
            }
        },
        
        // Проверка соответствия нажатой клавиши конфигурации
        matchesKey: function(e, config) {
            const keyMatch = e.key === config.key || 
                           e.key.toLowerCase() === config.key.toLowerCase() ||
                           e.code === config.key;
            
            const ctrlMatch = config.ctrl ? e.ctrlKey || e.metaKey : !e.ctrlKey && !e.metaKey;
            const altMatch = config.alt ? e.altKey : !e.altKey;
            const shiftMatch = config.shift ? e.shiftKey : !e.shiftKey;
            
            return keyMatch && ctrlMatch && altMatch && shiftMatch;
        },
        
        // Инициализация
        init: function() {
            document.addEventListener('keydown', this.handleKeyPress.bind(this));
            
            // Добавляем визуальную подсказку при наведении на элементы с горячими клавишами
            this.addVisualHints();
        },
        
        // Добавление визуальных подсказок
        addVisualHints: function() {
            // Можно добавить атрибуты data-hotkey к элементам для отображения подсказок
            document.querySelectorAll('[data-hotkey]').forEach(el => {
                const hotkeyName = el.getAttribute('data-hotkey');
                const config = this.keys[hotkeyName];
                if (config) {
                    const hint = this.formatHotkeyHint(config);
                    el.setAttribute('title', `${el.getAttribute('title') || ''} (${hint})`.trim());
                }
            });
        },
        
        // Форматирование подсказки горячей клавиши
        formatHotkeyHint: function(config) {
            const parts = [];
            if (config.ctrl) parts.push('Ctrl');
            if (config.alt) parts.push('Alt');
            if (config.shift) parts.push('Shift');
            parts.push(config.key.toUpperCase());
            return parts.join('+');
        }
    };
    
    // Функция показа справки по горячим клавишам
    function showHotkeysHelp() {
        const helpHtml = `
            <div class="modal fade" id="hotkeysHelpModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-keyboard"></i> Горячие клавиши
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Комбинация</th>
                                            <th>Действие</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${Object.entries(hotkeys.keys).map(([name, config]) => `
                                            <tr>
                                                <td><kbd>${hotkeys.formatHotkeyHint(config)}</kbd></td>
                                                <td>${config.description}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Удаляем старый модал, если есть
        const oldModal = document.getElementById('hotkeysHelpModal');
        if (oldModal) {
            oldModal.remove();
        }
        
        // Добавляем новый модал
        document.body.insertAdjacentHTML('beforeend', helpHtml);
        
        // Показываем модал
        const modal = new bootstrap.Modal(document.getElementById('hotkeysHelpModal'));
        modal.show();
        
        // Удаляем модал после закрытия
        document.getElementById('hotkeysHelpModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }
    
    // Инициализация при загрузке DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            hotkeys.init();
        });
    } else {
        hotkeys.init();
    }
    
    // Экспортируем для использования в других скриптах
    window.hotkeys = hotkeys;
    
})();

