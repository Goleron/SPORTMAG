"""
Эндпоинты корзины: список, добавление, обновление, удаление, валидация.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import CartItem
from .serializers import (
    CartItemSerializer,
    CartItemAddSerializer,
    CartSerializer
)
from .services import CartService
from ..common.permissions import IsBuyer
from ..common.exceptions import InsufficientStockError, EmptyCartError


class CartItemListAPIView(generics.ListCreateAPIView):
    """Список элементов корзины и добавление товара"""
    serializer_class = CartItemSerializer
    permission_classes = [IsBuyer]
    
    def get_queryset(self):
        """Получить корзину текущего пользователя"""
        return CartService.get_cart(self.request.user)
    
    def get_serializer_class(self):
        """Разные сериализаторы для GET и POST"""
        if self.request.method == 'POST':
            return CartItemAddSerializer
        return CartItemSerializer
    
    def create(self, request, *args, **kwargs):
        """Добавление товара в корзину"""
        serializer = CartItemAddSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cart_item = CartService.add_to_cart(
                    user=request.user,
                    product_id=serializer.validated_data['product_id'],
                    quantity=serializer.validated_data.get('quantity', 1)
                )
                response_serializer = CartItemSerializer(cart_item)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartItemDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление и удаление элемента корзины"""
    serializer_class = CartItemSerializer
    permission_classes = [IsBuyer]
    
    def get_queryset(self):
        """Получить корзину текущего пользователя"""
        return CartService.get_cart(self.request.user)
    
    def update(self, request, *args, **kwargs):
        """Обновление количества товара"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        quantity = request.data.get('quantity')
        
        if quantity is None:
            return Response(
                {'error': 'Необходимо указать количество'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart_item = CartService.update_cart_item(
                user=request.user,
                item_id=instance.id,
                quantity=int(quantity)
            )
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """Удаление товара из корзины"""
        instance = self.get_object()
        try:
            CartService.remove_from_cart(request.user, instance.id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['GET'])
@permission_classes([IsBuyer])
def cart_view(request):
    """
    Получить полную корзину с общей стоимостью
    
    GET /api/v1/cart/
    """
    cart_items = CartService.get_cart(request.user)
    cart_total = CartService.get_cart_total(request.user)
    
    serializer = CartItemSerializer(cart_items, many=True)
    
    return Response({
        'items': serializer.data,
        'total_items': cart_total['total_items'],
        'total_price': float(cart_total['total_price'])
    })


@api_view(['GET'])
@permission_classes([IsBuyer])
def cart_total_view(request):
    """
    Получить общую стоимость корзины
    
    GET /api/v1/cart/total/
    """
    cart_total = CartService.get_cart_total(request.user)
    
    return Response({
        'total_items': cart_total['total_items'],
        'total_price': float(cart_total['total_price'])
    })


@api_view(['DELETE'])
@permission_classes([IsBuyer])
def clear_cart_view(request):
    """
    Очистить корзину
    
    DELETE /api/v1/cart/clear/
    """
    count = CartService.clear_cart(request.user)
    
    return Response({
        'message': f'Корзина очищена. Удалено элементов: {count}'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsBuyer])
def validate_cart_view(request):
    """
    Валидация корзины перед созданием заказа
    
    POST /api/v1/cart/validate/
    """
    is_valid, errors = CartService.validate_cart(request.user)
    
    if is_valid:
        return Response({
            'valid': True,
            'message': 'Корзина валидна'
        })
    else:
        return Response({
            'valid': False,
            'errors': errors
        }, status=status.HTTP_400_BAD_REQUEST)

