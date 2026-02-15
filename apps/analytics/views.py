"""
Эндпоинты отчётов: продажи по продуктам, по месяцам, топ товаров, выручка, дашборд.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from .services import AnalyticsService
from .serializers import (
    SalesByProductSerializer,
    MonthlySalesSerializer,
    TopProductsSerializer,
    RevenueSerializer,
    DashboardStatsSerializer
)
from ..common.permissions import IsAnalyst


@api_view(['GET'])
@permission_classes([IsAnalyst])
def sales_by_product_view(request):
    """
    Продажи по продуктам
    
    GET /api/v1/analytics/sales-by-product/
    Query params:
        - category: ID категории (опционально)
        - date_from: начало периода (YYYY-MM-DD, опционально)
        - date_to: конец периода (YYYY-MM-DD, опционально)
    """
    category_id = request.query_params.get('category')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    if date_from:
        date_from = parse_date(date_from)
    if date_to:
        date_to = parse_date(date_to)
    
    results = AnalyticsService.get_sales_by_product(
        category_id=int(category_id) if category_id else None,
        date_from=date_from,
        date_to=date_to
    )
    
    serializer = SalesByProductSerializer(results, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAnalyst])
def monthly_sales_view(request):
    """
    Ежемесячные продажи
    
    GET /api/v1/analytics/monthly-sales/
    Query params:
        - year: год (опционально)
    """
    year = request.query_params.get('year')
    
    results = AnalyticsService.get_monthly_sales(
        year=int(year) if year else None
    )
    
    serializer = MonthlySalesSerializer(results, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAnalyst])
def top_products_view(request):
    """
    Топ товаров
    
    GET /api/v1/analytics/top-products/
    Query params:
        - limit: количество товаров (по умолчанию 10)
    """
    limit = request.query_params.get('limit', 10)
    
    try:
        limit = int(limit)
        if limit < 1 or limit > 100:
            return Response(
                {'error': 'Limit должен быть от 1 до 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError:
        return Response(
            {'error': 'Limit должен быть числом'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    results = AnalyticsService.get_top_products(limit=limit)
    
    serializer = TopProductsSerializer(results, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAnalyst])
def revenue_view(request):
    """
    Выручка за период
    
    GET /api/v1/analytics/revenue/
    Query params:
        - date_from: начало периода (YYYY-MM-DD, обязательно)
        - date_to: конец периода (YYYY-MM-DD, обязательно)
    """
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    if not date_from or not date_to:
        return Response(
            {'error': 'Необходимо указать date_from и date_to'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    date_from = parse_date(date_from)
    date_to = parse_date(date_to)
    
    if not date_from or not date_to:
        return Response(
            {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if date_from > date_to:
        return Response(
            {'error': 'date_from не может быть больше date_to'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    results = AnalyticsService.get_revenue_between(date_from, date_to)
    
    serializer = RevenueSerializer(results, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAnalyst])
def dashboard_view(request):
    """
    Общая статистика для дашборда
    
    GET /api/v1/analytics/dashboard/
    """
    stats = AnalyticsService.get_dashboard_stats()
    
    serializer = DashboardStatsSerializer(stats)
    return Response(serializer.data)

