"""
Маршруты аналитики: отчёты и экспорт в CSV.
"""
from django.urls import path
from . import views
from . import export_views

app_name = 'analytics'

urlpatterns = [
    path('sales-by-product/', views.sales_by_product_view, name='sales-by-product'),
    path('sales-by-product/export/csv/', export_views.export_sales_by_product_csv, name='sales-by-product-export-csv'),
    path('monthly-sales/', views.monthly_sales_view, name='monthly-sales'),
    path('monthly-sales/export/csv/', export_views.export_monthly_sales_csv, name='monthly-sales-export-csv'),
    path('top-products/', views.top_products_view, name='top-products'),
    path('top-products/export/csv/', export_views.export_top_products_csv, name='top-products-export-csv'),
    path('revenue/', views.revenue_view, name='revenue'),
    path('revenue/export/csv/', export_views.export_revenue_csv, name='revenue-export-csv'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]

