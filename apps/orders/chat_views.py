"""
API views для чата
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from .models import Chat, ChatMessage, Order
from .serializers import (
    ChatSerializer,
    ChatMessageSerializer,
    CreateChatMessageSerializer
)
from ..common.permissions import IsAdmin, IsBuyer, IsAnalyst


class ChatListAPIView(generics.ListAPIView):
    """Список чатов пользователя"""
    serializer_class = ChatSerializer
    permission_classes = [IsBuyer]
    
    def get_queryset(self):
        """Получить чаты в зависимости от роли"""
        user = self.request.user
        
        if user.role.name == 'Admin':
            # Админ видит все чаты
            return Chat.objects.select_related('order', 'user').prefetch_related(
                'messages__sender'
            ).filter(is_active=True)
        elif user.role.name == 'Analyst':
            # Аналитик видит чаты, где он участвовал или все активные
            return Chat.objects.select_related('order', 'user').prefetch_related(
                'messages__sender'
            ).filter(
                Q(is_active=True) & (
                    Q(messages__sender=user) | Q(order__status__in=['Pending', 'Processing', 'Shipped'])
                )
            ).distinct()
        else:
            # Пользователь видит только свои чаты
            return Chat.objects.select_related('order', 'user').prefetch_related(
                'messages__sender'
            ).filter(user=user, is_active=True)


class ChatDetailAPIView(generics.RetrieveAPIView):
    """Детали чата"""
    serializer_class = ChatSerializer
    permission_classes = [IsBuyer]
    
    def get_queryset(self):
        """Получить чат с проверкой прав"""
        user = self.request.user
        
        if user.role.name in ('Admin', 'Analyst'):
            return Chat.objects.select_related('order', 'user').prefetch_related(
                'messages__sender'
            ).all()
        else:
            return Chat.objects.select_related('order', 'user').prefetch_related(
                'messages__sender'
            ).filter(user=user)


@api_view(['POST'])
@permission_classes([IsBuyer])
def create_chat_view(request, order_id):
    """
    Создание чата для заказа
    
    POST /api/v1/orders/{order_id}/chat/
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Заказ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Проверяем права доступа
    if request.user.role.name not in ('Admin', 'Analyst'):
        if order.user != request.user:
            return Response(
                {'error': 'У вас нет доступа к этому заказу'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, есть ли активные заказы
        active_orders = Order.objects.filter(
            user=request.user,
            status__in=['Pending', 'Processing', 'Shipped', 'Delivered']
        ).count()
        
        if active_orders == 0:
            return Response(
                {'error': 'Чат доступен только при наличии активных заказов'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Проверяем, существует ли уже чат для этого заказа
    chat, created = Chat.objects.get_or_create(
        order=order,
        defaults={'user': order.user}
    )
    
    serializer = ChatSerializer(chat, context={'request': request})
    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsBuyer])
def create_chat_message_view(request, chat_id):
    """
    Создание сообщения в чате
    
    POST /api/v1/chats/{chat_id}/messages/
    """
    try:
        chat = Chat.objects.select_related('order', 'user').get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {'error': 'Чат не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Проверяем права доступа
    user = request.user
    if user.role.name not in ('Admin', 'Analyst'):
        if chat.user != user:
            return Response(
                {'error': 'У вас нет доступа к этому чату'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    serializer = CreateChatMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Создаем сообщение
    message = ChatMessage.objects.create(
        chat=chat,
        sender=user,
        message=serializer.validated_data['message']
    )
    
    # Обновляем время последнего обновления чата
    chat.save(update_fields=['updated_at'])
    
    response_serializer = ChatMessageSerializer(message)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsBuyer])
def mark_messages_read_view(request, chat_id):
    """
    Отметить сообщения как прочитанные
    
    POST /api/v1/chats/{chat_id}/mark-read/
    """
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {'error': 'Чат не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Проверяем права доступа
    user = request.user
    if user.role.name not in ('Admin', 'Analyst'):
        if chat.user != user:
            return Response(
                {'error': 'У вас нет доступа к этому чату'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Отмечаем все сообщения, которые не отправил текущий пользователь, как прочитанные
    updated = ChatMessage.objects.filter(
        chat=chat,
        is_read=False
    ).exclude(sender=user).update(is_read=True)
    
    return Response({
        'message': f'Отмечено {updated} сообщений как прочитанные'
    }, status=status.HTTP_200_OK)

