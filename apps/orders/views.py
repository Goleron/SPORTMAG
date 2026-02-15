"""
Эндпоинты заказов: список, создание, оплата, возвраты, транзакции.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Order, Transaction
from .serializers import (
    OrderSerializer,
    OrderListSerializer,
    TransactionSerializer,
    CreateOrderSerializer,
    CreatePaymentSerializer
)
from .services import OrderService, PaymentService
from ..common.permissions import IsAdmin, IsBuyer, IsOwnerOrAdmin, IsAnalyst
from ..common.exceptions import EmptyCartError, InvalidPaymentAmountError
from ..common.throttles import OrderCreateRateThrottle, PaymentRateThrottle


class OrderListAPIView(generics.ListAPIView):
    """Список заказов"""
    serializer_class = OrderListSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['order_date', 'total_amount', 'created_at']
    ordering = ['-order_date']
    
    def get_queryset(self):
        """Получить заказы в зависимости от роли пользователя"""
        user = self.request.user
        
        if user.role.name == 'Admin':
            return Order.objects.select_related('user').prefetch_related(
                'items__product',
                'transactions'
            ).all()
        else:
            return OrderService.get_user_orders(user)
    
    def get_permissions(self):
        """Только авторизованные пользователи"""
        return [IsBuyer()]


@api_view(['POST'])
@permission_classes([IsBuyer])
def create_order_view(request):
    """
    Создание заказа из корзины с rate limiting
    
    POST /api/v1/orders/create/
    """
    throttle = OrderCreateRateThrottle()
    if not throttle.allow_request(request, None):
        return Response(
            {'error': 'Превышен лимит запросов на создание заказов. Попробуйте позже.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        order, total_amount = OrderService.create_order_from_cart(request.user)
        response_serializer = OrderSerializer(order)
        return Response(
            {
                'order': response_serializer.data,
                'total_amount': float(total_amount),
                'message': 'Заказ успешно создан'
            },
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


class OrderDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление и удаление заказа"""
    serializer_class = OrderSerializer
    permission_classes = [IsBuyer | IsAdmin]
    
    def get_queryset(self):
        """Получить заказ с проверкой прав доступа"""
        user = self.request.user
        
        if user.role.name == 'Admin':
            return Order.objects.select_related('user').prefetch_related(
                'items__product',
                'transactions'
            ).all()
        else:
            return OrderService.get_user_orders(user)
    
    def get_object(self):
        """Получить заказ с проверкой прав"""
        order = super().get_object()
        if self.request.user.role.name != 'Admin':
            if order.user != self.request.user:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('У вас нет доступа к этому заказу')
        
        return order
    
    def update(self, request, *args, **kwargs):
        """Обновление заказа (только для админов)"""
        if request.user.role.name != 'Admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Только администраторы могут изменять заказы')
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Удаление заказа (только для админов)"""
        if request.user.role.name != 'Admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Только администраторы могут удалять заказы')
        
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@permission_classes([IsAdmin | IsAnalyst])
def update_order_status_view(request, pk):
    """
    Обновление статуса заказа (для администраторов и аналитиков)
    
    PATCH /api/v1/orders/{id}/status/
    """
    
    try:
        order = Order.objects.select_related('user').prefetch_related(
            'items__product',
            'transactions'
        ).get(id=pk)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Заказ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    new_status = request.data.get('status')
    if not new_status:
        return Response(
            {'error': 'Необходимо указать статус'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response(
            {'error': 'Неверный статус'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])
    if new_status in ('Completed', 'Refunded'):
        from apps.analytics.services import AnalyticsService
        AnalyticsService.invalidate_cache()
    
    serializer = OrderSerializer(order)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsBuyer])
def create_payment_view(request, order_id):
    """
    Создание платежа для заказа с rate limiting
    
    POST /api/v1/orders/{order_id}/pay/
    """
    # Применяем throttle для платежей
    throttle = PaymentRateThrottle()
    if not throttle.allow_request(request, None):
        return Response(
            {'error': 'Превышен лимит запросов на оплату. Попробуйте позже.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    serializer = CreatePaymentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем, что заказ принадлежит пользователю (если не админ)
    order = OrderService.get_order_by_id(order_id, request.user)
    if not order:
        return Response(
            {'error': 'Заказ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.user.role.name != 'Admin' and order.user != request.user:
        return Response(
            {'error': 'У вас нет доступа к этому заказу'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not order.can_be_paid():
        return Response(
            {'error': 'Заказ не может быть оплачен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Безопасная обработка данных карты
        from ..common.card_utils import sanitize_card_data, mask_card_number
        from ..common.models import Log
        
        use_saved_card = serializer.validated_data.get('use_saved_card')
        card_number = serializer.validated_data.get('card_number', '')
        card_cvv = serializer.validated_data.get('card_cvv', '')
        card_expiry = serializer.validated_data.get('card_expiry', '')
        
        # Если используется сохраненная карта, проверяем что она есть у пользователя
        if use_saved_card:
            saved_cards = request.user.get_saved_cards()
            saved_card = next((c for c in saved_cards if c.get('hash') == use_saved_card), None)
            if not saved_card:
                return Response(
                    {'error': 'Сохраненная карта не найдена'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Используем сохраненную карту - не требуем данные новой карты
            card_number = ''
            card_cvv = ''
            card_expiry = ''
        
        # Сохраняем карту, если пользователь запросил (только для новых карт)
        save_card = serializer.validated_data.get('save_card', False)
        if save_card and serializer.validated_data.get('payment_method') == 'Card' and not use_saved_card:
            cardholder_name = serializer.validated_data.get('cardholder_name', '')
            
            if card_number and cardholder_name:
                # Хешируем данные карты используя crypt (как пароль)
                from django.db import connection
                
                # Создаем хеш из номера карты и CVV (для безопасности)
                card_data = f"{card_number}{card_cvv}"
                # Используем crypt для хеширования
                with connection.cursor() as cursor:
                    cursor.execute("SELECT crypt(%s, gen_salt('bf'))", [card_data])
                    result = cursor.fetchone()
                    card_hash = result[0] if result else None
                
                if card_hash:
                    last_four = card_number[-4:] if len(card_number) >= 4 else card_number
                    request.user.add_saved_card(card_hash, last_four, cardholder_name)
        
        # Логируем платеж БЕЗ чувствительных данных карты
        sanitized_card_data = sanitize_card_data(card_number, card_cvv, card_expiry)
        if use_saved_card:
            sanitized_card_data = {'type': 'saved_card', 'hash': use_saved_card[:20] + '...'}
        Log.objects.create(
            level='INFO',
            message=f'Payment processing started for order #{order_id}',
            user_id=request.user.id,
            meta={
                'order_id': order_id,
                'amount': str(serializer.validated_data['amount']),
                'payment_method': serializer.validated_data['payment_method'],
                'card_data': sanitized_card_data,  # Только замаскированные данные
                'action': 'payment_processing'
            }
        )
        
        # Сохраняем адрес доставки, если он указан
        delivery_address = serializer.validated_data.get('delivery_address')
        if delivery_address:
            order.delivery_address = delivery_address
            # Если заказ был отменен, возвращаем его в статус Pending при оплате
            if order.status == 'Cancelled':
                order.status = 'Pending'
            order.save(update_fields=['delivery_address', 'status', 'updated_at'])
        
        transaction_obj, tx_status = PaymentService.create_payment(
            order_id=order_id,
            amount=serializer.validated_data['amount'],
            payment_method=serializer.validated_data['payment_method'],
            user=request.user
        )
        
        if transaction_obj:
            response_serializer = TransactionSerializer(transaction_obj)
            return Response(
                {
                    'transaction': response_serializer.data,
                    'status': tx_status,
                    'message': 'Платеж успешно обработан'
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {
                    'status': tx_status,
                    'error': 'Платеж не был обработан'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError as e:
        # Логируем ошибку БЕЗ данных карты
        Log.objects.create(
            level='ERROR',
            message=f'Payment failed for order #{order_id}: {str(e)}',
            user_id=request.user.id,
            meta={
                'order_id': order_id,
                'action': 'payment_failed',
                'error': str(e)
                # НЕ логируем данные карты
            }
        )
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        # Логируем неожиданные ошибки
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Unexpected error in payment processing: {e}', exc_info=True)
        
        Log.objects.create(
            level='ERROR',
            message=f'Unexpected error in payment processing for order #{order_id}',
            user_id=request.user.id if request.user.is_authenticated else None,
            meta={
                'order_id': order_id,
                'action': 'payment_error',
                'error_type': type(e).__name__
                # НЕ логируем полный traceback и данные карты
            }
        )
        return Response(
            {'error': 'Произошла ошибка при обработке платежа'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsBuyer])
def order_transactions_view(request, order_id):
    """
    История транзакций заказа
    
    GET /api/v1/orders/{order_id}/transactions/
    """
    order = OrderService.get_order_by_id(order_id, request.user)
    if not order:
        return Response(
            {'error': 'Заказ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.user.role.name != 'Admin' and order.user != request.user:
        return Response(
            {'error': 'У вас нет доступа к этому заказу'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    transactions = order.transactions.all()
    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def refund_transaction_view(request, transaction_id):
    """
    Возврат транзакции (только для администраторов)
    
    POST /api/v1/transactions/{id}/refund/
    """
    try:
        transaction_obj = Transaction.objects.select_related('order').get(id=transaction_id)
    except Transaction.DoesNotExist:
        return Response(
            {'error': 'Транзакция не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if not transaction_obj.can_be_refunded():
        return Response(
            {'error': 'Транзакция не может быть возвращена'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        message = PaymentService.refund_transaction(transaction_id, request.user)
        
        # Получаем обновленную транзакцию
        transaction_obj.refresh_from_db()
        serializer = TransactionSerializer(transaction_obj)
        
        return Response(
            {
                'transaction': serializer.data,
                'message': message
            },
            status=status.HTTP_200_OK
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

