-- ======================================================
-- Скрипт для добавления индексов производительности
-- Совместим с актуальной структурой БД
-- Использование: выполните в pgAdmin или через psql
-- ======================================================

SET search_path = shop, public;

-- ======================================================
-- 1. Индексы для таблицы orders
-- ======================================================

-- Индекс для фильтрации по статусу (часто используется в запросах)
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Индекс для сортировки по дате заказа
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date DESC);

-- Составной индекс для фильтрации по пользователю и статусу
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);

-- Составной индекс для фильтрации по статусу и дате (для аналитики)
CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders(status, order_date DESC);

-- ======================================================
-- 2. Индексы для таблицы order_items
-- ======================================================

-- Составной индекс для связи заказа и товара (часто используется в JOIN)
CREATE INDEX IF NOT EXISTS idx_order_items_order_product ON order_items(order_id, product_id);

-- Индекс для фильтрации по товару (для аналитики продаж)
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

-- Индекс для даты создания (для фильтрации по периодам)
CREATE INDEX IF NOT EXISTS idx_order_items_created_at ON order_items(created_at);

-- ======================================================
-- 3. Индексы для таблицы transactions
-- ======================================================

-- Индекс для фильтрации по статусу транзакций
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

-- Составной индекс для фильтрации по заказу и статусу
CREATE INDEX IF NOT EXISTS idx_transactions_order_status ON transactions(order_id, status);

-- Индекс для даты транзакции (для отчетов)
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- Индекс для transaction_date (для сортировки)
CREATE INDEX IF NOT EXISTS idx_transactions_transaction_date ON transactions(transaction_date DESC);

-- Индекс для transaction_date (для сортировки)
CREATE INDEX IF NOT EXISTS idx_transactions_transaction_date ON transactions(transaction_date DESC);

-- ======================================================
-- 4. Индексы для таблицы products
-- ======================================================

-- Составной индекс для фильтрации доступных товаров в наличии
-- Частичный индекс для оптимизации
CREATE INDEX IF NOT EXISTS idx_products_available_stock ON products(is_available, stock_quantity) 
WHERE is_available = TRUE AND stock_quantity > 0;

-- Индекс для сортировки по дате создания
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at DESC);

-- Индекс для поиска по SKU (уже есть через UNIQUE, но для документации)
-- CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku); -- уже есть через UNIQUE

-- ======================================================
-- 5. Индексы для таблицы categories
-- ======================================================

-- Индекс для поиска дочерних категорий (parent_id уже может быть проиндексирован через FK)
-- Но добавим явно для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);

-- Индекс для поиска по slug (уже есть через UNIQUE)
-- CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug); -- уже есть через UNIQUE

-- ======================================================
-- 6. Индексы для таблицы cart_items
-- ======================================================

-- Составной индекс для поиска товаров в корзине пользователя
-- (уже есть UNIQUE на user_id, product_id, но добавим для оптимизации JOIN)
-- CREATE INDEX IF NOT EXISTS idx_cart_items_user_product ON cart_items(user_id, product_id); -- уже есть через UNIQUE

-- Индекс для фильтрации по пользователю (уже есть в основном скрипте как idx_cart_user)
-- Проверяем и создаем если нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'shop' 
        AND tablename = 'cart_items' 
        AND indexname = 'idx_cart_user'
    ) THEN
        CREATE INDEX idx_cart_user ON cart_items(user_id);
    END IF;
END $$;

-- ======================================================
-- 7. Индексы для таблицы logs
-- ======================================================

-- Индекс для фильтрации по уровню лога
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);

-- Составной индекс для фильтрации по пользователю и уровню
CREATE INDEX IF NOT EXISTS idx_logs_user_level ON logs(user_id, level);

-- Индекс для сортировки по дате (уже есть idx_logs_user_ts, но добавим отдельный для ts)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'shop' 
        AND tablename = 'logs' 
        AND indexname = 'idx_logs_ts'
    ) THEN
        CREATE INDEX idx_logs_ts ON logs(ts DESC);
    END IF;
END $$;

-- ======================================================
-- 8. Индексы для таблицы audit_log
-- ======================================================

-- Индекс для фильтрации по таблице
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);

-- Составной индекс для фильтрации по таблице и действию
CREATE INDEX IF NOT EXISTS idx_audit_log_table_action ON audit_log(table_name, action);

-- Индекс для сортировки по дате
CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log(ts DESC);

-- Индекс для фильтрации по пользователю
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);

-- ======================================================
-- 9. Индексы для таблицы users
-- ======================================================

-- Индекс для поиска активных пользователей (частичный индекс)
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active) WHERE is_active = TRUE;

-- Составной индекс для поиска по роли и активности
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role_id, is_active);

-- Индекс для поиска по email (уже есть через UNIQUE)
-- CREATE INDEX IF NOT EXISTS idx_users_email ON users(email); -- уже есть через UNIQUE

-- ======================================================
-- 10. Индексы для таблицы backups
-- ======================================================

-- Индекс для сортировки по дате создания
CREATE INDEX IF NOT EXISTS idx_backups_ts ON backups(ts DESC);

-- Индекс для фильтрации по статусу
CREATE INDEX IF NOT EXISTS idx_backups_status ON backups(status);

-- Индекс для фильтрации по создателю
CREATE INDEX IF NOT EXISTS idx_backups_created_by ON backups(created_by);

-- ======================================================
-- 11. Индексы для таблицы product_attribute_values
-- ======================================================

-- Индекс для поиска по товару
CREATE INDEX IF NOT EXISTS idx_product_attr_values_product ON product_attribute_values(product_id);

-- Индекс для поиска по атрибуту
CREATE INDEX IF NOT EXISTS idx_product_attr_values_attribute ON product_attribute_values(attribute_id);

-- Составной индекс для поиска значений атрибутов товара
-- (уже есть UNIQUE на product_id, attribute_id, value, но добавим для оптимизации)
-- CREATE INDEX IF NOT EXISTS idx_product_attr_values_product_attr ON product_attribute_values(product_id, attribute_id); -- уже есть через UNIQUE

-- ======================================================
-- 12. Комментарии к индексам
-- ======================================================

COMMENT ON INDEX idx_orders_status IS 'Индекс для быстрой фильтрации заказов по статусу';
COMMENT ON INDEX idx_orders_order_date IS 'Индекс для сортировки заказов по дате';
COMMENT ON INDEX idx_order_items_order_product IS 'Составной индекс для JOIN заказов и товаров';
COMMENT ON INDEX idx_products_available_stock IS 'Частичный индекс для быстрого поиска доступных товаров';
COMMENT ON INDEX idx_cart_items_user_product IS 'Индекс для быстрого поиска товаров в корзине пользователя (через UNIQUE)';

-- ======================================================
-- 13. Обновление статистики для оптимизатора запросов
-- ======================================================

-- Обновление статистики для оптимизатора запросов
ANALYZE orders;
ANALYZE order_items;
ANALYZE products;
ANALYZE categories;
ANALYZE transactions;
ANALYZE cart_items;
ANALYZE logs;
ANALYZE audit_log;
ANALYZE users;
ANALYZE backups;
ANALYZE product_attribute_values;

-- ======================================================
-- 14. Проверка созданных индексов
-- ======================================================

-- Выводим список всех индексов для проверки
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'shop'
ORDER BY tablename, indexname;

-- ======================================================
-- Конец скрипта
-- ======================================================

-- Сообщение об успешном выполнении
DO $$
BEGIN
    RAISE NOTICE 'Индексы производительности успешно созданы!';
    RAISE NOTICE 'Проверьте список индексов выше для подтверждения.';
END $$;

