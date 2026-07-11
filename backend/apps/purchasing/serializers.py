from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.accounting import services as accounting_services
from apps.core.numbering import next_value
from apps.inventory.services import stock_in

from .models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchasePayment,
    PurchaseRequest,
    PurchaseRequestItem,
)


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    quantity_outstanding = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id", "product", "product_name", "variant", "quantity", "unit_price",
            "discount_percent", "tax_percent", "quantity_received", "quantity_outstanding", "line_total",
        ]
        read_only_fields = ["quantity_received"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "number", "supplier", "supplier_name", "purchase_request", "status", "order_date",
            "expected_date", "notes", "subtotal", "discount_total", "tax_total", "total", "amount_paid",
            "balance_due", "items", "created_at",
        ]
        read_only_fields = [
            "number", "status", "subtotal", "discount_total", "tax_total", "total", "amount_paid",
            "purchase_request",
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        company = validated_data["company"]
        validated_data["number"] = next_value(company, "purchase_order", default_prefix="PO-")
        order = PurchaseOrder.objects.create(**validated_data)
        items = [PurchaseOrderItem(company=company, purchase_order=order, **item) for item in items_data]
        PurchaseOrderItem.objects.bulk_create(items)
        order.recalculate_totals(items)
        order.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])
        return order


class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = GoodsReceiptItem
        fields = ["id", "purchase_order_item", "product", "product_name", "variant", "quantity", "unit_cost"]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    items = GoodsReceiptItemSerializer(many=True)
    supplier_name = serializers.CharField(source="purchase_order.supplier.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id", "number", "purchase_order", "supplier_name", "warehouse", "warehouse_name",
            "received_date", "notes", "items", "created_at",
        ]
        read_only_fields = ["number"]

    def validate_items(self, items):
        for item in items:
            po_item = item["purchase_order_item"]
            if item["quantity"] > po_item.quantity_outstanding:
                raise serializers.ValidationError(
                    f"Cannot receive {item['quantity']} of {po_item.product.name}: only "
                    f"{po_item.quantity_outstanding} outstanding on the purchase order."
                )
        return items

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        company = validated_data["company"]
        user = validated_data.get("created_by")
        purchase_order = validated_data["purchase_order"]
        warehouse = validated_data["warehouse"]

        validated_data["number"] = next_value(company, "goods_receipt", default_prefix="GRN-")
        receipt = GoodsReceipt.objects.create(**validated_data)

        total_cost = Decimal("0")
        total_tax = Decimal("0")
        for item_data in items_data:
            GoodsReceiptItem.objects.create(company=company, goods_receipt=receipt, **item_data)
            stock_in(
                company=company, warehouse=warehouse, product=item_data["product"],
                variant=item_data.get("variant"), quantity=item_data["quantity"],
                unit_cost=item_data["unit_cost"], reference=receipt.number,
                reason="Goods receipt", user=user,
            )
            po_item = item_data["purchase_order_item"]
            po_item.quantity_received += item_data["quantity"]
            po_item.save(update_fields=["quantity_received"])

            line_cost = item_data["quantity"] * item_data["unit_cost"]
            total_cost += line_cost
            total_tax += line_cost * po_item.tax_percent / Decimal("100")

        all_items = purchase_order.items.all()
        if all(i.quantity_received >= i.quantity for i in all_items):
            purchase_order.status = PurchaseOrder.Status.RECEIVED
        else:
            purchase_order.status = PurchaseOrder.Status.PARTIALLY_RECEIVED
        purchase_order.save(update_fields=["status", "updated_at"])

        accounting_services.record_goods_receipt(receipt, total_cost, total_tax)

        return receipt


class PurchasePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasePayment
        fields = ["id", "purchase_order", "amount", "method", "reference", "paid_at"]
        read_only_fields = ["paid_at"]


class PurchaseRequestItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseRequestItem
        fields = ["id", "product", "product_name", "variant", "quantity", "unit_price",
                  "discount_percent", "tax_percent", "line_total"]


class PurchaseRequestSerializer(serializers.ModelSerializer):
    items = PurchaseRequestItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    requested_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default=None)
    approved_by_name = serializers.CharField(source="approved_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = PurchaseRequest
        fields = [
            "id", "number", "supplier", "supplier_name", "status", "request_date", "expected_date",
            "notes", "subtotal", "discount_total", "tax_total", "total", "requested_by_name",
            "approved_by_name", "approved_at", "rejection_reason", "items", "created_at",
        ]
        read_only_fields = [
            "number", "status", "subtotal", "discount_total", "tax_total", "total",
            "approved_at", "rejection_reason",
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        company = validated_data["company"]
        validated_data["number"] = next_value(company, "purchase_request", default_prefix="PR-")
        purchase_request = PurchaseRequest.objects.create(**validated_data)
        items = [PurchaseRequestItem(company=company, purchase_request=purchase_request, **item) for item in items_data]
        PurchaseRequestItem.objects.bulk_create(items)
        purchase_request.recalculate_totals(items)
        purchase_request.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])
        return purchase_request
