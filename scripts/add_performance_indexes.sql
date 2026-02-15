-- Дополнительные индексы для оптимизации производительности
-- Этот скрипт добавляет индексы для часто используемых запросов

SET search_path = shop, public;

-- Индексы для таблицы orders
-- Индекс для фильтрации по статусу (часто используется в запросах)
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Индекс для сортировки по дате заказа
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date DESC);

-- Составной индекс для фильтрации по пользователю и статусу
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);

-- Составной индекс для фильтрации по статусу и дате (для аналитики)
CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders(status, order_date DESC);

-- Индексы для таблицы order_items
-- Составной индекс для связи заказа и товара (часто используется в JOIN)
CREATE INDEX IF NOT EXISTS idx_order_items_order_product ON order_items(order_id, product_id);

-- Индекс для фильтрации по товару (для аналитики продаж)
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

-- Индекс для даты создания (для фильтрации по периодам)
CREATE INDEX IF NOT EXISTS idx_order_items_created_at ON order_items(created_at);

-- Индексы для таблицы transactions
-- Индекс для фильтрации по статусу транзакций
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

-- Составной индекс для фильтрации по заказу и статусу
CREATE INDEX IF NOT EXISTS idx_transactions_order_status ON transactions(order_id, status);

-- Индекс для даты транзакции (для отчетов)
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- Индексы для таблицы products
-- Индекс для поиска по SKU (уже есть UNIQUE, но можно добавить для полноты)
-- UNIQUE уже создает индекс, но добавим явно для документации
-- CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku); -- уже есть через UNIQUE

-- Составной индекс для фильтрации доступных товаров в наличии
CREATE INDEX IF NOT EXISTS idx_products_available_stock ON products(is_available, stock_quantity) 
WHERE is_available = TRUE AND stock_quantity > 0;

-- Индекс для поиска по категории (уже может быть через FK, но явно)
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);

-- Индекс для сортировки по дате создания
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at DESC);

-- Индексы для таблицы categories
-- Индекс для поиска дочерних категорий
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);

-- Индекс для поиска по slug (уже есть UNIQUE, но для документации)
-- CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug); -- уже есть через UNIQUE

-- Индексы для таблицы cart_items
-- Составной индекс для поиска товаров в корзине пользователя
CREATE INDEX IF NOT EXISTS idx_cart_items_user_product ON cart_items(user_id, product_id);

-- Индекс для фильтрации по пользователю
CREATE INDEX IF NOT EXISTS idx_cart_items_user ON cart_items(user_id);

-- Индексы для таблицы logs
-- Индекс для фильтрации по уровню лога
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);

-- Составной индекс для фильтрации по пользователю и уровню
CREATE INDEX IF NOT EXISTS idx_logs_user_level ON logs(user_id, level);

-- Индекс для сортировки по дате
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at DESC);

-- Индексы для таблицы audit_log
-- Индекс для фильтрации по таблице
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);

-- Составной индекс для фильтрации по таблице и действию
CREATE INDEX IF NOT EXISTS idx_audit_log_table_action ON audit_log(table_name, action);

-- Индекс для сортировки по дате
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);

-- Индексы для таблицы users
-- Индекс для поиска активных пользователей
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active) WHERE is_active = TRUE;

-- Составной индекс для поиска по роли и активности
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role_id, is_active);

-- Индексы для таблицы backups
-- Индекс для сортировки по дате создания
CREATE INDEX IF NOT EXISTS idx_backups_created_at ON backups(created_at DESC);

-- Индекс для фильтрации по статусу
CREATE INDEX IF NOT EXISTS idx_backups_status ON backups(status);

-- Комментарии к индексам
COMMENT ON INDEX idx_orders_status IS 'Индекс для быстрой фильтрации заказов по статусу';
COMMENT ON INDEX idx_orders_order_date IS 'Индекс для сортировки заказов по дате';
COMMENT ON INDEX idx_order_items_order_product IS 'Составной индекс для JOIN заказов и товаров';
COMMENT ON INDEX idx_products_available_stock IS 'Частичный индекс для быстрого поиска доступных товаров';
COMMENT ON INDEX idx_cart_items_user_product IS 'Индекс для быстрого поиска товаров в корзине пользователя';

-- Статистика для оптимизатора запросов
ANALYZE orders;
ANALYZE order_items;
ANALYZE products;
ANALYZE categories;
ANALYZE transactions;
ANALYZE cart_items;

