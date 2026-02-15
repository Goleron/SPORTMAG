"""
Views для общих функций, включая внешние API
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from .external_api import get_exchange_rate_api, get_delivery_api
from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    summary="Получить курсы валют",
    description="Получить актуальные курсы валют относительно базовой валюты",
    parameters=[
        OpenApiParameter(
            name='base',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Базовая валюта (по умолчанию RUB)',
            required=False,
        ),
    ],
    tags=['External API'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_exchange_rates(request):
    """
    Получить курсы валют
    """
    base_currency = request.query_params.get('base', 'RUB').upper()
    
    api = get_exchange_rate_api()
    rates = api.get_exchange_rates(base_currency)
    
    if rates is None:
        return Response(
            {'error': 'Не удалось получить курсы валют'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    return Response({
        'base_currency': base_currency,
        'rates': rates,
        'timestamp': api.get_exchange_rates.__name__  # В реальности здесь был бы timestamp
    })


@extend_schema(
    summary="Конвертировать валюту",
    description="Конвертировать сумму из одной валюты в другую",
    parameters=[
        OpenApiParameter(
            name='amount',
            type=float,
            location=OpenApiParameter.QUERY,
            description='Сумма для конвертации',
            required=True,
        ),
        OpenApiParameter(
            name='from',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Исходная валюта',
            required=True,
        ),
        OpenApiParameter(
            name='to',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Целевая валюта',
            required=True,
        ),
    ],
    tags=['External API'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def convert_currency(request):
    """
    Конвертировать валюту
    """
    try:
        amount = Decimal(str(request.query_params.get('amount')))
        from_currency = request.query_params.get('from', 'RUB').upper()
        to_currency = request.query_params.get('to', 'USD').upper()
    except (ValueError, TypeError):
        return Response(
            {'error': 'Неверные параметры запроса'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    api = get_exchange_rate_api()
    converted = api.convert_currency(amount, from_currency, to_currency)
    
    if converted is None:
        return Response(
            {'error': 'Не удалось конвертировать валюту'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    return Response({
        'original_amount': str(amount),
        'original_currency': from_currency,
        'converted_amount': str(converted),
        'converted_currency': to_currency,
    })


@extend_schema(
    summary="Рассчитать стоимость доставки",
    description="Рассчитать стоимость доставки на основе веса, расстояния и типа доставки",
    parameters=[
        OpenApiParameter(
            name='weight',
            type=float,
            location=OpenApiParameter.QUERY,
            description='Вес в кг',
            required=True,
        ),
        OpenApiParameter(
            name='distance',
            type=float,
            location=OpenApiParameter.QUERY,
            description='Расстояние в км',
            required=True,
        ),
        OpenApiParameter(
            name='type',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Тип доставки (standard, express, overnight)',
            required=False,
        ),
    ],
    tags=['External API'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculate_delivery(request):
    """
    Рассчитать стоимость доставки
    """
    try:
        weight = float(request.query_params.get('weight', 0))
        distance = float(request.query_params.get('distance', 0))
        delivery_type = request.query_params.get('type', 'standard')
    except (ValueError, TypeError):
        return Response(
            {'error': 'Неверные параметры запроса'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if weight <= 0 or distance <= 0:
        return Response(
            {'error': 'Вес и расстояние должны быть больше нуля'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    api = get_delivery_api()
    cost = api.calculate_delivery_cost(weight, distance, delivery_type)
    delivery_time = api.get_delivery_time(distance, delivery_type)
    
    if cost is None:
        return Response(
            {'error': 'Не удалось рассчитать стоимость доставки'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    return Response({
        'weight_kg': weight,
        'distance_km': distance,
        'delivery_type': delivery_type,
        'cost': str(cost),
        'delivery_time_days': delivery_time,
    })


@extend_schema(
    summary="Получить доступные валюты",
    description="Получить список доступных валют для конвертации",
    tags=['External API'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_available_currencies(request):
    """
    Получить список доступных валют
    """
    api = get_exchange_rate_api()
    currencies = api.get_available_currencies()
    
    return Response({
        'currencies': currencies,
    })

