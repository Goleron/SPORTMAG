"""
Views для экспорта заказов в CSV
"""
import csv
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Order, OrderItem
from .services import OrderService
from ..common.permissions import IsAdmin, IsAnalyst
from ..common.models import Log


@extend_schema(
    summary="Экспорт заказов в CSV",
    description="Экспорт списка заказов в CSV формат с возможностью фильтрации",
    parameters=[
        OpenApiParameter(
            name='status',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Фильтр по статусу заказа',
            required=False,
        ),
        OpenApiParameter(
            name='date_from',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Дата начала периода (YYYY-MM-DD)',
            required=False,
        ),
        OpenApiParameter(
            name='date_to',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Дата окончания периода (YYYY-MM-DD)',
            required=False,
        ),
        OpenApiParameter(
            name='detailed',
            type=bool,
            location=OpenApiParameter.QUERY,
            description='Включить детали позиций заказа',
            required=False,
        ),
    ],
    tags=['Orders'],
)
@api_view(['GET'])
@permission_classes([IsAdmin | IsAnalyst])
def export_orders_csv(request):
    """
    Экспорт заказов в CSV
    
    GET /api/v1/orders/export/csv/
    """
    try:
        # Параметры фильтрации
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        detailed = request.query_params.get('detailed', 'false').lower() == 'true'
        
        # Получаем заказы
        queryset = Order.objects.select_related('user').prefetch_related('items__product').all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)
        
        queryset = queryset.order_by('-order_date')
        
        # Логируем экспорт
        Log.objects.create(
            level='INFO',
            message=f'Orders export to CSV: {queryset.count()} orders',
            user_id=request.user.id if request.user.is_authenticated else None,
            meta={
                'status_filter': status_filter,
                'date_from': date_from,
                'date_to': date_to,
                'detailed': detailed,
                'action': 'orders_export'
            }
        )
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = 'orders_export_detailed.csv' if detailed else 'orders_export.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        if detailed:
            # Детальный экспорт с позициями заказов
            writer.writerow([
                'ID заказа', 'Дата заказа', 'Пользователь', 'Email', 'Статус',
                'ID позиции', 'Товар', 'SKU', 'Количество', 'Цена за единицу', 'Сумма позиции',
                'Общая сумма заказа', 'Создан', 'Обновлен'
            ])
            
            for order in queryset:
                items = order.items.select_related('product').all()
                if items:
                    for item in items:
                        writer.writerow([
                            order.id,
                            order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
                            order.user.username if order.user else '',
                            order.user.email if order.user else '',
                            order.status,
                            item.id,
                            item.product.name if item.product else '',
                            item.product.sku if item.product else '',
                            item.quantity,
                            str(item.price_at_purchase),
                            str(item.get_total_price()),
                            str(order.total_amount),
                            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                            order.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                        ])
                else:
                    # Заказ без позиций
                    writer.writerow([
                        order.id,
                        order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
                        order.user.username if order.user else '',
                        order.user.email if order.user else '',
                        order.status,
                        '', '', '', '', '', '',
                        str(order.total_amount),
                        order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        order.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    ])
        else:
            # Краткий экспорт
            writer.writerow([
                'ID заказа', 'Дата заказа', 'Пользователь', 'Email', 'Статус',
                'Сумма заказа', 'Количество позиций', 'Создан', 'Обновлен'
            ])
            
            for order in queryset:
                items_count = order.items.count()
                writer.writerow([
                    order.id,
                    order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
                    order.user.username if order.user else '',
                    order.user.email if order.user else '',
                    order.status,
                    str(order.total_amount),
                    items_count,
                    order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    order.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                ])
        
        return response
        
    except Exception as e:
        # Логируем ошибку
        Log.objects.create(
            level='ERROR',
            message=f'Failed to export orders to CSV: {str(e)}',
            user_id=request.user.id if request.user.is_authenticated else None,
            meta={'action': 'orders_export_failed', 'error': str(e)}
        )
        return HttpResponse(
            f'Ошибка при экспорте заказов: {str(e)}',
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content_type='text/plain; charset=utf-8'
        )

