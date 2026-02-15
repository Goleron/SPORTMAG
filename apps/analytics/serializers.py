"""
Сериализаторы отчётов аналитики (продажи, выручка, дашборд).
"""
from rest_framework import serializers


class SalesByProductSerializer(serializers.Serializer):
    """Сериализатор для продаж по продуктам"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    total_quantity_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class MonthlySalesSerializer(serializers.Serializer):
    """Сериализатор для ежемесячных продаж"""
    month_start = serializers.DateField()
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    orders_count = serializers.IntegerField()


class TopProductsSerializer(serializers.Serializer):
    """Сериализатор для топ товаров"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    qty_sold = serializers.IntegerField()


class RevenueSerializer(serializers.Serializer):
    """Сериализатор для выручки за период"""
    month_date = serializers.DateField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class DashboardStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики дашборда"""
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_orders = serializers.IntegerField()
    active_users = serializers.IntegerField()
    top_products = TopProductsSerializer(many=True)

