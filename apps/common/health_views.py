"""
Health check endpoints для мониторинга системы
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from .external_api import ExchangeRateAPI


@extend_schema(
    summary="Health check системы",
    description="Проверка общего состояния системы",
    tags=['Health'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Общая проверка здоровья системы
    
    GET /api/health/
    """
    checks = {
        'status': 'ok',
        'database': False,
        'cache': False,
    }
    
    # Проверка БД
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks['database'] = True
    except Exception:
        checks['status'] = 'error'
        checks['database'] = False
    
    # Проверка кэша
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            checks['cache'] = True
    except Exception:
        checks['status'] = 'error'
        checks['cache'] = False
    
    http_status = status.HTTP_200_OK if checks['status'] == 'ok' else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return Response(checks, status=http_status)


@extend_schema(
    summary="Проверка базы данных",
    description="Проверка подключения к базе данных",
    tags=['Health'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_db(request):
    """
    Проверка подключения к БД
    
    GET /api/health/db/
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # Проверяем схему shop
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'shop'")
            table_count = cursor.fetchone()[0]
        
        return Response({
            'status': 'ok',
            'database': 'connected',
            'version': version.split(',')[0] if version else 'unknown',
            'tables_count': table_count
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'database': 'disconnected',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@extend_schema(
    summary="Проверка кэша",
    description="Проверка работы кэша",
    tags=['Health'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_cache(request):
    """
    Проверка работы кэша
    
    GET /api/health/cache/
    """
    try:
        test_key = 'health_check_cache'
        test_value = 'ok'
        
        cache.set(test_key, test_value, 10)
        retrieved = cache.get(test_key)
        
        if retrieved == test_value:
            return Response({
                'status': 'ok',
                'cache': 'working'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'cache': 'not_working',
                'error': 'Cache get/set mismatch'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response({
            'status': 'error',
            'cache': 'error',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@extend_schema(
    summary="Проверка внешних API",
    description="Проверка доступности внешних API",
    tags=['Health'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_external(request):
    """
    Проверка внешних API
    
    GET /api/health/external/
    """
    checks = {
        'status': 'ok',
        'exchange_rate_api': False,
    }
    
    # Проверка API курсов валют
    try:
        api = ExchangeRateAPI()
        rates = api.get_exchange_rates('USD')
        if rates:
            checks['exchange_rate_api'] = True
        else:
            checks['status'] = 'partial'
    except Exception:
        checks['status'] = 'partial'
        checks['exchange_rate_api'] = False
    
    http_status = status.HTTP_200_OK if checks['status'] in ('ok', 'partial') else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return Response(checks, status=http_status)

