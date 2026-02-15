"""
Маршруты корзины и админского управления корзиной пользователей.
"""
from django.urls import path
from . import views
from . import admin_views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_view, name='cart'),
    path('total/', views.cart_total_view, name='cart-total'),
    path('clear/', views.clear_cart_view, name='cart-clear'),
    path('validate/', views.validate_cart_view, name='cart-validate'),
    path('items/', views.CartItemListAPIView.as_view(), name='cart-item-list'),
    path('items/<int:pk>/', views.CartItemDetailAPIView.as_view(), name='cart-item-detail'),
    path('admin/users/<int:user_id>/', admin_views.admin_user_cart_view, name='admin-user-cart'),
    path('admin/users/<int:user_id>/items/', admin_views.admin_add_to_user_cart_view, name='admin-add-to-user-cart'),
    path('admin/users/<int:user_id>/items/<int:item_id>/', admin_views.admin_update_user_cart_item_view, name='admin-update-user-cart-item'),
    path('admin/users/<int:user_id>/items/<int:item_id>/delete/', admin_views.admin_delete_user_cart_item_view, name='admin-delete-user-cart-item'),
    path('admin/users/<int:user_id>/clear/', admin_views.admin_clear_user_cart_view, name='admin-clear-user-cart'),
]

