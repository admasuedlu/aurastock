from rest_framework import serializers

from apps.core.numbering import next_value

from .models import Invoice, InvoiceItem, Quotation, QuotationItem, SalesOrder, SalesOrderItem, SalesPayment


class QuotationItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = QuotationItem
        fields = ["id", "product", "product_name", "variant", "quantity", "unit_price",
                  "discount_percent", "tax_percent", "line_total"]


class SalesOrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    quantity_outstanding = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = ["id", "product", "product_name", "variant", "quantity", "unit_price",
                  "discount_percent", "tax_percent", "quantity_invoiced", "quantity_outstanding", "line_total"]
        read_only_fields = ["quantity_invoiced"]


class InvoiceItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ["id", "product", "product_name", "variant", "quantity", "unit_price",
                  "discount_percent", "tax_percent", "line_total"]


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Quotation
        fields = [
            "id", "number", "customer", "customer_name", "status", "issue_date", "expiry_date",
            "notes", "subtotal", "discount_total", "tax_total", "total", "items", "created_at",
        ]
        read_only_fields = ["number", "status", "subtotal", "discount_total", "tax_total", "total"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        company = validated_data["company"]
        validated_data["number"] = next_value(company, "quotation", default_prefix="QUO-")
        quotation = Quotation.objects.create(**validated_data)
        items = [QuotationItem(company=company, quotation=quotation, **item) for item in items_data]
        QuotationItem.objects.bulk_create(items)
        quotation.recalculate_totals(items)
        quotation.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])
        return quotation


class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = SalesOrder
        fields = [
            "id", "number", "customer", "customer_name", "quotation", "status", "order_date",
            "notes", "subtotal", "discount_total", "tax_total", "total", "items", "created_at",
        ]
        read_only_fields = ["number", "status", "subtotal", "discount_total", "tax_total", "total"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        company = validated_data["company"]
        validated_data["number"] = next_value(company, "sales_order", default_prefix="SO-")
        order = SalesOrder.objects.create(**validated_data)
        items = [SalesOrderItem(company=company, sales_order=order, **item) for item in items_data]
        SalesOrderItem.objects.bulk_create(items)
        order.recalculate_totals(items)
        order.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])
        return order


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "customer", "customer_name", "sales_order", "warehouse", "warehouse_name",
            "status", "issue_date", "due_date", "notes", "subtotal", "discount_total", "tax_total",
            "total", "amount_paid", "balance_due", "items", "created_at",
        ]
        read_only_fields = ["number", "status", "subtotal", "discount_total", "tax_total", "total", "amount_paid"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        company = validated_data["company"]
        validated_data["number"] = next_value(company, "invoice", default_prefix="INV-")
        invoice = Invoice.objects.create(**validated_data)
        items = [InvoiceItem(company=company, invoice=invoice, **item) for item in items_data]
        InvoiceItem.objects.bulk_create(items)
        invoice.recalculate_totals(items)
        invoice.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])
        return invoice


class SalesPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesPayment
        fields = ["id", "invoice", "amount", "method", "reference", "paid_at"]
        read_only_fields = ["paid_at"]
