"""
URL-маршруты для веб-интерфейса магазина
"""
from django.urls import path
from . import views
from . import admin_views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.product_list, name='product_list'),
    path('catalog/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:cart_item_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.orders_list, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/payment/', views.payment_view, name='payment'),
    path('orders/<int:order_id>/chat/', views.order_chat_view, name='order_chat'),
    path('register/', views.register, name='register'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('login/', views.login_view, name='login'),
    path('password-reset/', views.password_reset_request_view, name='password_reset_request'),
    path('reset-password/<str:token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
    
    # Analytics
    path('analytics/', admin_views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/sales-by-product/', admin_views.sales_by_product, name='analytics_sales_by_product'),
    path('analytics/monthly-sales/', admin_views.monthly_sales, name='analytics_monthly_sales'),
    path('analytics/top-products/', admin_views.top_products, name='analytics_top_products'),
    path('analytics/revenue/', admin_views.revenue, name='analytics_revenue'),
    path('analytics/reports/', admin_views.analytics_reports, name='analytics_reports'),
    path('analytics/sales-by-product/export/csv/', lambda r: admin_views.analytics_export_csv(r, 'sales-by-product'), name='analytics_export_sales_by_product_csv'),
    path('analytics/monthly-sales/export/csv/', lambda r: admin_views.analytics_export_csv(r, 'monthly-sales'), name='analytics_export_monthly_sales_csv'),
    path('analytics/revenue/export/csv/', lambda r: admin_views.analytics_export_csv(r, 'revenue'), name='analytics_export_revenue_csv'),
    path('analytics/top-products/export/csv/', lambda r: admin_views.analytics_export_csv(r, 'top-products'), name='analytics_export_top_products_csv'),
    
    # Admin
    path('admin-panel/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/products/', admin_views.admin_products, name='admin_products'),
    path('admin-panel/products/export/csv/', admin_views.admin_export_products_csv, name='admin_export_products_csv'),
    path('admin-panel/categories/', admin_views.admin_categories, name='admin_categories'),
    path('admin-panel/categories/export/csv/', admin_views.admin_export_categories_csv, name='admin_export_categories_csv'),
    path('admin-panel/users/', admin_views.admin_users, name='admin_users'),
    path('admin-panel/orders/', admin_views.admin_orders, name='admin_orders'),
    path('admin-panel/transactions/', admin_views.admin_transactions, name='admin_transactions'),
    path('admin-panel/cart-items/', admin_views.admin_cart_items, name='admin_cart_items'),
    path('admin-panel/logs/', admin_views.admin_logs, name='admin_logs'),
    path('admin-panel/logs/export/pdf/', admin_views.admin_logs_export_pdf, name='admin_logs_export_pdf'),
    path('admin-panel/audit/', admin_views.admin_audit, name='admin_audit'),
    path('admin-panel/backups/', admin_views.admin_backups, name='admin_backups'),
    path('admin-panel/backups/<int:backup_id>/download/', admin_views.admin_download_backup, name='admin_download_backup'),
]

