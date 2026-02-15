"""
Маршруты каталога: категории, товары, атрибуты, импорт/экспорт CSV.
"""
from django.urls import path
from . import views
from . import export_views
from . import import_views

app_name = 'catalog'

urlpatterns = [
    path('categories/', views.CategoryListAPIView.as_view(), name='category-list'),
    path('categories/tree/', views.CategoryTreeAPIView.as_view(), name='category-tree'),
    path('categories/<int:pk>/', views.CategoryDetailAPIView.as_view(), name='category-detail'),
    path('categories/<int:pk>/products/', views.category_products_view, name='category-products'),
    path('categories/export/csv/', export_views.export_categories_csv, name='category-export-csv'),
    path('categories/import/csv/', import_views.import_categories_csv, name='category-import-csv'),
    path('products/', views.ProductListAPIView.as_view(), name='product-list'),
    path('products/<int:pk>/', views.ProductDetailAPIView.as_view(), name='product-detail'),
    path('products/<int:product_id>/attributes/', views.ProductAttributeListAPIView.as_view(), name='product-attributes'),
    path('products/<int:product_id>/attributes/<int:pk>/', views.ProductAttributeDetailAPIView.as_view(), name='product-attribute-detail'),
    path('products/export/csv/', export_views.export_products_csv, name='product-export-csv'),
    path('products/import/csv/', import_views.import_products_csv, name='product-import-csv'),
    path('attributes/', views.AttributeListAPIView.as_view(), name='attribute-list'),
    path('attributes/<int:pk>/', views.AttributeDetailAPIView.as_view(), name='attribute-detail'),
]

