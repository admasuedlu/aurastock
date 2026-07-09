from django.db import transaction
from rest_framework import serializers

from apps.core.numbering import next_value
from apps.inventory.services import stock_out

from .models import POSSession, POSTransaction, POSTransactionItem


class POSSessionSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source="cashier.get_full_name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = POSSession
        fields = [
            "id", "warehouse", "warehouse_name", "cashier", "cashier_name", "status",
            "opening_cash", "closing_cash", "expected_cash", "cash_variance",
            "opened_at", "closed_at",
        ]
        read_only_fields = [
            "cashier", "status", "closing_cash", "expected_cash", "cash_variance", "opened_at", "closed_at",
        ]


class POSTransactionItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = POSTransactionItem
        fields = ["id", "product", "product_name", "variant", "quantity", "unit_price",
                  "discount_percent", "tax_percent", "line_total"]


class POSTransactionSerializer(serializers.ModelSerializer):
    items = POSTransactionItemSerializer(many=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="Walk-in")
    change_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = POSTransaction
        fields = [
            "id", "number", "session", "customer", "customer_name", "payment_method",
            "amount_tendered", "status", "subtotal", "discount_total", "tax_total", "total",
            "change_due", "items", "created_at",
        ]
        read_only_fields = ["number", "status", "subtotal", "discount_total", "tax_total", "total"]

    def validate_session(self, session):
        if session.status != POSSession.Status.OPEN:
            raise serializers.ValidationError("This till session is closed.")
        return session

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        if not items_data:
            raise serializers.ValidationError({"items": "A sale needs at least one line item."})

        company = validated_data["company"]
        session = validated_data["session"]
        user = validated_data.get("created_by")

        validated_data["number"] = next_value(company, "pos_transaction", default_prefix="POS-")
        pos_transaction = POSTransaction.objects.create(**validated_data)

        items = [POSTransactionItem(company=company, transaction=pos_transaction, **item) for item in items_data]
        POSTransactionItem.objects.bulk_create(items)
        pos_transaction.recalculate_totals(items)
        pos_transaction.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])

        for item in items:
            stock_out(
                company=company, warehouse=session.warehouse, product=item.product, variant=item.variant,
                quantity=item.quantity, reference=pos_transaction.number, reason="POS sale", user=user,
            )

        return pos_transaction
