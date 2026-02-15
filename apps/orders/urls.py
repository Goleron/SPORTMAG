"""
Маршруты заказов, транзакций и чата поддержки.
"""
from django.urls import path
from . import views
from . import chat_views
from . import export_views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderListAPIView.as_view(), name='order-list'),
    path('create/', views.create_order_view, name='order-create'),
    path('<int:pk>/', views.OrderDetailAPIView.as_view(), name='order-detail'),
    path('<int:pk>/status/', views.update_order_status_view, name='order-status'),
    path('<int:order_id>/pay/', views.create_payment_view, name='order-pay'),
    path('<int:order_id>/transactions/', views.order_transactions_view, name='order-transactions'),
    path('<int:order_id>/chat/', chat_views.create_chat_view, name='order-chat'),
    path('export/csv/', export_views.export_orders_csv, name='order-export-csv'),
    path('transactions/<int:transaction_id>/refund/', views.refund_transaction_view, name='transaction-refund'),
    path('chats/', chat_views.ChatListAPIView.as_view(), name='chat-list'),
    path('chats/<int:pk>/', chat_views.ChatDetailAPIView.as_view(), name='chat-detail'),
    path('chats/<int:chat_id>/messages/', chat_views.create_chat_message_view, name='chat-message-create'),
    path('chats/<int:chat_id>/mark-read/', chat_views.mark_messages_read_view, name='chat-mark-read'),
]

