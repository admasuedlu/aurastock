from rest_framework import serializers

from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem
from apps.sales.models import Invoice, InvoiceItem, Quotation, QuotationItem, SalesOrder, SalesOrderItem


from .models import PortalAccount


class PortalLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PortalAccessGrantSerializer(serializers.Serializer):
    """Staff input to open (or reset) a portal login for one of their own
    customers/suppliers."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)


class PortalAccountStaffSerializer(serializers.ModelSerializer):
    """What a staff member sees about an existing portal login. Never exposes
    the password hash."""

    class Meta:
        model = PortalAccount
        fields = ["id", "email", "account_type", "is_active", "last_login_at", "created_at"]


class _PortalLineItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        fields = ["product_name", "quantity", "unit_price", "discount_percent", "tax_percent", "line_total"]


class PortalQuotationItemSerializer(_PortalLineItemSerializer):
    class Meta(_PortalLineItemSerializer.Meta):
        model = QuotationItem


class PortalSalesOrderItemSerializer(_PortalLineItemSerializer):
    class Meta(_PortalLineItemSerializer.Meta):
        model = SalesOrderItem


class PortalInvoiceItemSerializer(_PortalLineItemSerializer):
    class Meta(_PortalLineItemSerializer.Meta):
        model = InvoiceItem


class PortalPurchaseOrderItemSerializer(_PortalLineItemSerializer):
    class Meta(_PortalLineItemSerializer.Meta):
        model = PurchaseOrderItem


class PortalQuotationSerializer(serializers.ModelSerializer):
    items = PortalQuotationItemSerializer(many=True, read_only=True)

    class Meta:
        model = Quotation
        fields = ["id", "number", "status", "issue_date", "expiry_date", "notes",
                  "subtotal", "discount_total", "tax_total", "total", "items"]


class PortalSalesOrderSerializer(serializers.ModelSerializer):
    items = PortalSalesOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = SalesOrder
        fields = ["id", "number", "status", "order_date", "notes",
                  "subtotal", "discount_total", "tax_total", "total", "items"]


class PortalInvoiceSerializer(serializers.ModelSerializer):
    items = PortalInvoiceItemSerializer(many=True, read_only=True)
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "number", "status", "issue_date", "due_date", "notes",
                  "subtotal", "discount_total", "tax_total", "total",
                  "amount_paid", "balance_due", "items"]


class PortalPurchaseOrderSerializer(serializers.ModelSerializer):
    items = PortalPurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ["id", "number", "status", "order_date", "expected_date", "notes",
                  "subtotal", "discount_total", "tax_total", "total", "items"]
