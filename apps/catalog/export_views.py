"""
Экспорт категорий и товаров в CSV.
"""
import csv
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import Product, Category
from .services import ProductService
from ..common.permissions import IsAdmin, IsAnalyst


@api_view(['GET'])
@permission_classes([IsAdmin | IsAnalyst])
def export_products_csv(request):
    """
    Экспорт товаров в CSV
    
    GET /api/v1/products/export/csv/
    """
    category_id = request.query_params.get('category')
    search = request.query_params.get('search')
    queryset = ProductService.get_products_with_filters(
        category_id=int(category_id) if category_id else None,
        search=search,
        available_only=False
    )
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'SKU', 'Название', 'Описание', 'Категория', 
        'Цена', 'Количество на складе', 'Доступен', 'Создан', 'Обновлен'
    ])
    for product in queryset:
        writer.writerow([
            product.id,
            product.sku,
            product.name,
            product.description or '',
            product.category.name if product.category else '',
            str(product.price),
            product.stock_quantity,
            'Да' if product.is_available else 'Нет',
            product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            product.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    
    return response


@api_view(['GET'])
@permission_classes([IsAdmin])
def export_categories_csv(request):
    """
    Экспорт категорий в CSV
    
    GET /api/v1/categories/export/csv/
    """
    queryset = Category.objects.select_related('parent').all()
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="categories_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Название', 'Описание', 'Родительская категория', 'Создан', 'Обновлен'])
    
    for category in queryset:
        writer.writerow([
            category.id,
            category.name,
            category.description or '',
            category.parent.name if category.parent else '',
            category.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            category.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    
    return response

