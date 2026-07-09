from django.contrib import admin

from .models import StockItem, StockMovement, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "company", "branch", "is_active"]
    list_filter = ["company", "is_active"]


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ["product", "warehouse", "quantity_on_hand", "reserved_quantity", "average_cost"]
    list_filter = ["company", "warehouse"]
    search_fields = ["product__name", "product__sku"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["movement_type", "product", "warehouse", "quantity", "created_at"]
    list_filter = ["company", "warehouse", "movement_type"]
    search_fields = ["product__name", "product__sku", "reference"]
