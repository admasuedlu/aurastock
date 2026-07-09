from django.db import transaction
from rest_framework import serializers

from apps.core.numbering import next_value
from apps.inventory.services import stock_in

from .models import GoodsReceipt, GoodsReceiptItem, PurchaseOrder, PurchaseOrderItem, PurchasePayment


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
            "id", "number", "supplier", "supplier_name", "status", "order_date", "expected_date",
            "notes", "subtotal", "discount_total", "tax_total", "total", "amount_paid", "balance_due",
            "items", "created_at",
        ]
        read_only_fields = ["number", "status", "subtotal", "discount_total", "tax_total", "total", "amount_paid"]

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

        all_items = purchase_order.items.all()
        if all(i.quantity_received >= i.quantity for i in all_items):
            purchase_order.status = PurchaseOrder.Status.RECEIVED
        else:
            purchase_order.status = PurchaseOrder.Status.PARTIALLY_RECEIVED
        purchase_order.save(update_fields=["status", "updated_at"])

        return receipt


class PurchasePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasePayment
        fields = ["id", "purchase_order", "amount", "method", "reference", "paid_at"]
        read_only_fields = ["paid_at"]
