"""
Экспорт отчётов аналитики в CSV.
"""
import csv
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from django.utils.dateparse import parse_date
from .services import AnalyticsService
from ..common.permissions import IsAnalyst


@api_view(['GET'])
@permission_classes([IsAnalyst])
def export_sales_by_product_csv(request):
    """
    Экспорт продаж по продуктам в CSV
    
    GET /api/v1/analytics/sales-by-product/export/csv/
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
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="sales_by_product_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID товара', 'Название товара', 'Количество продаж', 'Общая сумма'])
    
    for item in results:
        writer.writerow([
            item.get('product_id', ''),
            item.get('product_name', ''),
            item.get('total_quantity_sold', 0),
            str(item.get('total_revenue', 0)),
        ])
    
    return response


@api_view(['GET'])
@permission_classes([IsAnalyst])
def export_monthly_sales_csv(request):
    """
    Экспорт ежемесячных продаж в CSV
    
    GET /api/v1/analytics/monthly-sales/export/csv/
    """
    year = request.query_params.get('year')
    
    results = AnalyticsService.get_monthly_sales(year=int(year) if year else None)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="monthly_sales_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Месяц', 'Количество заказов', 'Общая сумма'])
    
    for item in results:
        writer.writerow([
            item.get('month_start', ''),
            item.get('orders_count', 0),
            str(item.get('total_revenue', 0)),
        ])
    
    return response


@api_view(['GET'])
@permission_classes([IsAnalyst])
def export_revenue_csv(request):
    """
    Экспорт выручки в CSV
    
    GET /api/v1/analytics/revenue/export/csv/
    """
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    if not date_from or not date_to:
        return HttpResponse('Необходимо указать date_from и date_to', status=400)
    
    date_from = parse_date(date_from)
    date_to = parse_date(date_to)
    
    results = AnalyticsService.get_revenue_between(date_from, date_to)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="revenue_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Месяц', 'Выручка'])
    
    for item in results:
        writer.writerow([
            item.get('month_date', ''),
            str(item.get('revenue', 0)),
        ])
    
    return response


@api_view(['GET'])
@permission_classes([IsAnalyst])
def export_top_products_csv(request):
    """
    Экспорт топ товаров в CSV
    
    GET /api/v1/analytics/top-products/export/csv/
    """
    limit = request.query_params.get('limit', 10)
    
    results = AnalyticsService.get_top_products(limit=int(limit) if limit else 10)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="top_products_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID товара', 'Название товара', 'Количество продаж'])
    
    for item in results:
        writer.writerow([
            item.get('product_id', ''),
            item.get('product_name', ''),
            item.get('qty_sold', 0),
        ])
    
    return response
