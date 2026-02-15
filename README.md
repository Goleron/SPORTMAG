# Sport Shop API

> **Интернет-магазин спортивных товаров** — REST API и веб-интерфейс на Django (курсовая работа).

[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14-9B59B6)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://www.python.org/)

---

## О проекте

Бэкенд и веб-клиент для интернет-магазина спортивных товаров: каталог с категориями и атрибутами, корзина, заказы, оплата, аналитика, поддержка (чат) и интеграции с внешними API (курсы валют, расчёт доставки).

### Возможности

| Модуль | Описание |
|--------|----------|
| **Каталог** | Категории (дерево), товары, EAV-атрибуты, импорт/экспорт CSV |
| **Аккаунты** | Регистрация, JWT-авторизация, роли, сброс пароля по email |
| **Корзина** | CRUD позиций, валидация, админ-управление корзинами пользователей |
| **Заказы** | Создание заказа, статусы, транзакции, возвраты, экспорт в CSV |
| **Поддержка** | Чаты по заказам, сообщения, отметка прочтения |
| **Аналитика** | Продажи по товарам/месяцам, топ товаров, выручка, дашборд, экспорт отчётов |
| **Внешние API** | Курсы валют, конвертация, расчёт стоимости доставки |
| **Инфраструктура** | Health checks (app, DB, cache, external), логирование, кэш, throttle |

### Стек

- **Backend:** Django 5, Django REST Framework, Simple JWT (blacklist), drf-spectacular (OpenAPI)
- **БД:** PostgreSQL (схема `shop`), кэш в памяти
- **Дополнительно:** django-cors-headers, django-filter, python-decouple, requests, reportlab (PDF/отчёты)
- **Веб-интерфейс:** отдельное Django-приложение на порту 8001, работа через API

---

## Структура репозитория

```
4kursach/
├── config/                 # Настройки Django (settings, urls, wsgi)
├── apps/
│   ├── accounts/           # Пользователи, роли, auth (JWT, register, password reset)
│   ├── catalog/           # Категории, товары, атрибуты, импорт/экспорт
│   ├── cart/              # Корзина и админ-управление корзиной
│   ├── orders/            # Заказы, транзакции, чаты, экспорт
│   ├── analytics/         # Отчёты, дашборд, экспорт в CSV
│   └── common/            # Внешние API, health, админ-эндпоинты
├── web/                   # Веб-интерфейс (Django, порт 8001)
│   ├── shop/              # API-клиент, views, формы
│   ├── templates/         # HTML-шаблоны
│   └── website/           # settings, urls веб-приложения
├── scripts/               # Резервное копирование, проверки, индексы
├── templates/             # Общие шаблоны (если есть)
├── manage.py              # Точка входа API-сервера
└── requirements.txt       # Зависимости (см. web/requirements.txt)
```

---

## Быстрый старт

### Требования

- Python 3.10+
- PostgreSQL 15+ (создайте БД и схему `shop`)
- Переменные окружения или файл `.env` в корне

### 1. Клонирование и окружение

```bash
git clone <repo-url>
cd 4kursach
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r web/requirements.txt
```

### 2. База данных

В PostgreSQL:

```sql
CREATE DATABASE kurs_sport_shop;
\c kurs_sport_shop
CREATE SCHEMA shop;
```


### 3. Миграции и суперпользователь

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Запуск API

```bash
python manage.py runserver 8000
```

API: **http://127.0.0.1:8000**

- Документация: **http://127.0.0.1:8000/api/docs/** (Swagger)  
- ReDoc: **http://127.0.0.1:8000/api/redoc/**  
- Админка: **http://127.0.0.1:8000/admin/**

### 5. Запуск веб-интерфейса

В отдельном терминале:

```bash
cd web
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```

Веб-сайт: **http://127.0.0.1:8001**

В `web/website/settings.py` или через `.env` можно задать `API_BASE_URL` (по умолчанию `http://127.0.0.1:8000/api/v1`).

---

## API

| Префикс | Назначение |
|---------|------------|
| `api/v1/auth/*` | Регистрация, логин, refresh, me, сброс пароля |
| `api/v1/roles/`, `api/v1/users/` | Роли и пользователи |
| `api/v1/categories/`, `api/v1/products/`, `api/v1/attributes/` | Каталог, импорт/экспорт CSV |
| `api/v1/cart/` | Корзина и админ-управление корзиной |
| `api/v1/orders/` | Заказы, оплата, транзакции, чаты, экспорт |
| `api/v1/analytics/` | Отчёты, дашборд, экспорт в CSV |
| `api/v1/external/*` | Курсы валют, конвертация, расчёт доставки |
| `api/v1/health/` | Health check (общий, db, cache, external) |
| `api/v1/admin/` | Админские эндпоинты (бэкапы и др.) |

Аутентификация: **Bearer JWT** (получить токен через `auth/login/`). В Swagger/ReDoc можно передать токен и вызывать защищённые методы.

---

## Скрипты

- `scripts/backup.py` — резервное копирование БД  
- `scripts/restore.py` — восстановление из бэкапа  
- `scripts/run_all_checks.py` — проверки целостности и нормализации  
- `scripts/README_INDEXES.md`, `scripts/README_APPLY_INDEXES.md` — индексы БД  
- `scripts/setup_auto_backup.md` — настройка автоматического бэкапа  

Подробности — в соответствующих файлах в `scripts/`.
