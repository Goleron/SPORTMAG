"""
Маршруты внешних API (курсы валют, доставка) и health checks.
"""
from django.urls import path
from . import views
from . import health_views

app_name = 'common'

urlpatterns = [
    path('external/exchange-rates/', views.get_exchange_rates, name='exchange-rates'),
    path('external/convert-currency/', views.convert_currency, name='convert-currency'),
    path('external/currencies/', views.get_available_currencies, name='available-currencies'),
    path('external/delivery/calculate/', views.calculate_delivery, name='calculate-delivery'),
    path('health/', health_views.health_check, name='health'),
    path('health/db/', health_views.health_db, name='health-db'),
    path('health/cache/', health_views.health_cache, name='health-cache'),
    path('health/external/', health_views.health_external, name='health-external'),
]

