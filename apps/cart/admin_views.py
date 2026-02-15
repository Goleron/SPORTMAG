"""
Админские эндпоинты управления корзиной пользователей.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import CartItem
from .serializers import CartItemSerializer
from .services import CartService
from ..common.permissions import IsAdmin

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_user_cart_view(request, user_id):
    """
    Получить корзину пользователя (для администраторов)
    
    GET /api/v1/admin/cart/users/{user_id}/
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    cart_items = CartService.get_cart(user)
    cart_total = CartService.get_cart_total(user)
    
    serializer = CartItemSerializer(cart_items, many=True)
    
    return Response({
        'user_id': user.id,
        'user_username': user.username,
        'items': serializer.data,
        'total_items': cart_total['total_items'],
        'total_price': float(cart_total['total_price'])
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def admin_add_to_user_cart_view(request, user_id):
    """
    Добавить товар в корзину пользователя (для администраторов)
    
    POST /api/v1/admin/cart/users/{user_id}/items/
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)
    
    if not product_id:
        return Response(
            {'error': 'Необходимо указать product_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        cart_item = CartService.add_to_cart(
            user=user,
            product_id=product_id,
            quantity=quantity
        )
        serializer = CartItemSerializer(cart_item)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdmin])
def admin_update_user_cart_item_view(request, user_id, item_id):
    """
    Обновить элемент корзины пользователя (для администраторов)
    
    PUT/PATCH /api/v1/admin/cart/users/{user_id}/items/{item_id}/
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        cart_item = CartItem.objects.get(id=item_id, user=user)
    except CartItem.DoesNotExist:
        return Response(
            {'error': 'Элемент корзины не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    quantity = request.data.get('quantity')
    if quantity is None:
        return Response(
            {'error': 'Необходимо указать количество'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        updated_item = CartService.update_cart_item(
            user=user,
            item_id=item_id,
            quantity=int(quantity)
        )
        serializer = CartItemSerializer(updated_item)
        return Response(serializer.data)
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@permission_classes([IsAdmin])
def admin_delete_user_cart_item_view(request, user_id, item_id):
    """
    Удалить элемент корзины пользователя (для администраторов)
    
    DELETE /api/v1/admin/cart/users/{user_id}/items/{item_id}/
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        CartService.remove_from_cart(user, item_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@permission_classes([IsAdmin])
def admin_clear_user_cart_view(request, user_id):
    """
    Очистить корзину пользователя (для администраторов)
    
    DELETE /api/v1/admin/cart/users/{user_id}/clear/
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    count = CartService.clear_cart(user)
    return Response({
        'message': f'Корзина пользователя очищена. Удалено элементов: {count}'
    }, status=status.HTTP_200_OK)

