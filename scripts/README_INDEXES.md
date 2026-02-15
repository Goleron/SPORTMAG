# Скрипт для добавления индексов производительности

## Описание

Скрипт `add_performance_indexes.sql` добавляет дополнительные индексы к базе данных для оптимизации часто выполняемых запросов.

## Использование

```bash
# Подключитесь к базе данных
psql -U postgres -d kurs_sport_shop

# Выполните скрипт
\i scripts/add_performance_indexes.sql
```

Или через Django:

```bash
python manage.py dbshell < scripts/add_performance_indexes.sql
```

## Добавляемые индексы

### Таблица `orders`
- `idx_orders_status` - фильтрация по статусу
- `idx_orders_order_date` - сортировка по дате заказа
- `idx_orders_user_status` - составной индекс (пользователь + статус)
- `idx_orders_status_date` - составной индекс (статус + дата)

### Таблица `order_items`
- `idx_order_items_order_product` - JOIN заказов и товаров
- `idx_order_items_product` - фильтрация по товару
- `idx_order_items_created_at` - фильтрация по дате

### Таблица `transactions`
- `idx_transactions_status` - фильтрация по статусу
- `idx_transactions_order_status` - составной индекс
- `idx_transactions_created_at` - сортировка по дате

### Таблица `products`
- `idx_products_available_stock` - частичный индекс для доступных товаров
- `idx_products_category` - фильтрация по категории
- `idx_products_created_at` - сортировка по дате

### Таблица `categories`
- `idx_categories_parent` - поиск дочерних категорий

### Таблица `cart_items`
- `idx_cart_items_user_product` - поиск товаров в корзине
- `idx_cart_items_user` - фильтрация по пользователю

### Таблицы `logs` и `audit_log`
- Индексы для фильтрации и сортировки по уровням, таблицам и датам

## Примечания

- Все индексы создаются с условием `IF NOT EXISTS`, поэтому скрипт можно запускать многократно
- После создания индексов выполняется `ANALYZE` для обновления статистики оптимизатора
- Индексы могут увеличить время вставки данных, но значительно ускоряют SELECT запросы

## Проверка индексов

После выполнения скрипта можно проверить созданные индексы:

```sql
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'shop'
ORDER BY tablename, indexname;
```

