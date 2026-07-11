from django.contrib import admin

from .models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchasePayment,
    PurchaseRequest,
    PurchaseRequestItem,
)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


class PurchasePaymentInline(admin.TabularInline):
    model = PurchasePayment
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["number", "supplier", "company", "status", "total", "amount_paid"]
    list_filter = ["company", "status"]
    inlines = [PurchaseOrderItemInline, PurchasePaymentInline]


class GoodsReceiptItemInline(admin.TabularInline):
    model = GoodsReceiptItem
    extra = 0


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ["number", "purchase_order", "warehouse", "company", "received_date"]
    list_filter = ["company", "warehouse"]
    inlines = [GoodsReceiptItemInline]


class PurchaseRequestItemInline(admin.TabularInline):
    model = PurchaseRequestItem
    extra = 0


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ["number", "supplier", "company", "status", "total", "approved_by"]
    list_filter = ["company", "status"]
    inlines = [PurchaseRequestItemInline]
