# Инструкция по применению индексов производительности

## Описание

Скрипт `apply_performance_indexes.sql` добавляет дополнительные индексы к базе данных для оптимизации часто выполняемых запросов. Скрипт совместим с актуальной структурой БД.

## Способ 1: Выполнение в pgAdmin

1. Откройте pgAdmin
2. Подключитесь к серверу PostgreSQL
3. Найдите базу данных `kurs_sport_shop`
4. Кликните правой кнопкой на базе данных → **Query Tool**
5. Откройте файл `scripts/apply_performance_indexes.sql`
6. Нажмите **Execute** (F5) или кнопку ▶️

## Способ 2: Выполнение через psql

```bash
# Подключитесь к базе данных
psql -U postgres -d kurs_sport_shop

# Выполните скрипт
\i scripts/apply_performance_indexes.sql
```

Или одной командой:

```bash
psql -U postgres -d kurs_sport_shop -f scripts/apply_performance_indexes.sql
```

## Способ 3: Через Django dbshell

```bash
python manage.py dbshell < scripts/apply_performance_indexes.sql
```

## Что делает скрипт

1. **Создает индексы** для оптимизации запросов:
   - Фильтрация по статусам
   - Сортировка по датам
   - JOIN операции
   - Поиск по связанным таблицам

2. **Проверяет существующие индексы** - не создает дубликаты

3. **Обновляет статистику** (ANALYZE) для оптимизатора запросов

4. **Выводит список** всех созданных индексов для проверки

## Добавляемые индексы

### Таблица `orders`
- `idx_orders_status` - фильтрация по статусу
- `idx_orders_order_date` - сортировка по дате
- `idx_orders_user_status` - составной (пользователь + статус)
- `idx_orders_status_date` - составной (статус + дата)

### Таблица `order_items`
- `idx_order_items_order_product` - JOIN заказов и товаров
- `idx_order_items_product` - фильтрация по товару
- `idx_order_items_created_at` - фильтрация по дате

### Таблица `transactions`
- `idx_transactions_status` - фильтрация по статусу
- `idx_transactions_order_status` - составной индекс
- `idx_transactions_created_at` - сортировка по дате
- `idx_transactions_transaction_date` - сортировка по дате транзакции

### Таблица `products`
- `idx_products_available_stock` - частичный индекс для доступных товаров
- `idx_products_created_at` - сортировка по дате

### Таблица `categories`
- `idx_categories_parent` - поиск дочерних категорий

### Таблица `cart_items`
- Проверка и создание `idx_cart_user` если отсутствует

### Таблица `logs`
- `idx_logs_level` - фильтрация по уровню
- `idx_logs_user_level` - составной индекс
- `idx_logs_ts` - сортировка по дате (поле `ts`)

### Таблица `audit_log`
- `idx_audit_log_table_name` - фильтрация по таблице
- `idx_audit_log_table_action` - составной индекс
- `idx_audit_log_ts` - сортировка по дате (поле `ts`)
- `idx_audit_log_user_id` - фильтрация по пользователю

### Таблица `users`
- `idx_users_is_active` - частичный индекс для активных пользователей
- `idx_users_role_active` - составной индекс

### Таблица `backups`
- `idx_backups_ts` - сортировка по дате (поле `ts`)
- `idx_backups_status` - фильтрация по статусу
- `idx_backups_created_by` - фильтрация по создателю

### Таблица `product_attribute_values`
- `idx_product_attr_values_product` - поиск по товару
- `idx_product_attr_values_attribute` - поиск по атрибуту

## Проверка после выполнения

После выполнения скрипта проверьте созданные индексы:

```sql
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'shop'
ORDER BY tablename, indexname;
```

## Примечания

- Все индексы создаются с условием `IF NOT EXISTS`, поэтому скрипт можно запускать многократно
- Скрипт учитывает существующие индексы из основного скрипта БД
- После создания индексов выполняется `ANALYZE` для обновления статистики
- Индексы могут увеличить время вставки данных, но значительно ускоряют SELECT запросы

## Откат (если нужно)

Если нужно удалить индексы:

```sql
-- Удаление всех индексов из скрипта (осторожно!)
DROP INDEX IF EXISTS shop.idx_orders_status;
DROP INDEX IF EXISTS shop.idx_orders_order_date;
DROP INDEX IF EXISTS shop.idx_orders_user_status;
DROP INDEX IF EXISTS shop.idx_orders_status_date;
-- ... и так далее для всех индексов
```

**Внимание:** Не удаляйте индексы, созданные через UNIQUE или PRIMARY KEY ограничения!


