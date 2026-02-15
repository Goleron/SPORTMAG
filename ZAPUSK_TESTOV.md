# Команды для запуска тестов

Запуск из **корня проекта** (где лежит `manage.py` для API — папка `4kursach`, не `web`). Перед запуском: поднять PostgreSQL, выполнить `python manage.py migrate`, при необходимости установить зависимости из `requirements.txt` и `requirements-test.txt`.

---

## Все тесты (функциональные, интеграционные, БД, безопасность)

```bash
python manage.py test --verbosity=2
```

---

## По приложениям

```bash
# Каталог (товары, категории)
python manage.py test apps.catalog.tests --verbosity=2

# Аккаунты (пользователи, аутентификация, настройки)
python manage.py test apps.accounts.tests --verbosity=2

# Корзина
python manage.py test apps.cart.tests --verbosity=2

# Заказы
python manage.py test apps.orders.tests --verbosity=2

# Аналитика
python manage.py test apps.analytics.tests --verbosity=2

# Общие (логи, аудит, бэкапы)
python manage.py test apps.common.tests --verbosity=2
```

---

## Интеграционные и тесты БД/транзакций

```bash
python manage.py test tests.integration_tests tests.database_tests tests.transaction_tests --verbosity=2
```

---

## Нагрузочное тестирование (Locust)

API должен быть запущен на `http://127.0.0.1:8000`. Порты 8000 и 8001 при этом заняты — это нормально.

**Вариант 1 — скрипт (рекомендуется):**
```cmd
run_load_test.bat
```
Откроется Locust на порту **8090** (чтобы не конфликтовать с 8089). В браузере: **http://127.0.0.1:8090**

**Вариант 2 — вручную:**
```bash
pip install locust
locust -f tests/load_test.py --host=http://127.0.0.1:8000 --web-port=8090
```
Затем открыть в браузере **http://127.0.0.1:8090**. Если порт 8090 занят, заменить на `--web-port=8091`.

В веб-интерфейсе: указать число пользователей (Number of users), RPS (Spawn rate), нажать **Start swarming**.

---

## Линтинг (как в CI)

```bash
pip install flake8
flake8 apps/ --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 apps/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```
