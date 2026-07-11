from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel
from apps.sales.models import PaymentMethod, _Document, _LineItem


class PurchaseOrder(_Document):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        APPROVED = "approved", "Approved"
        PARTIALLY_RECEIVED = "partially_received", "Partially received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30)
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="purchase_orders")
    purchase_request = models.ForeignKey(
        "purchasing.PurchaseRequest", on_delete=models.SET_NULL, related_name="purchase_orders",
        null=True, blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    order_date = models.DateField(auto_now_add=True)
    expected_date = models.DateField(null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = ("company", "number")
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    @property
    def balance_due(self) -> Decimal:
        return self.total - self.amount_paid


class PurchaseOrderItem(_LineItem):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, related_name="+", null=True, blank=True)
    quantity_received = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))

    @property
    def quantity_outstanding(self) -> Decimal:
        return self.quantity - self.quantity_received


class GoodsReceipt(CompanyScopedModel):
    number = models.CharField(max_length=30)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="goods_receipts")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="goods_receipts")
    received_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        unique_together = ("company", "number")
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class GoodsReceiptItem(CompanyScopedModel):
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="items")
    purchase_order_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT, related_name="receipt_items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, related_name="+", null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4)
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    serial_numbers = models.JSONField(default=list, blank=True)


class PurchasePayment(CompanyScopedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-paid_at"]


class PurchaseRequest(_Document):
    """An internal request to buy, sitting upstream of a purchase order. It
    runs through an approval workflow (draft -> submitted -> approved/rejected)
    before an approved request can be converted into an actual PO -- the buy
    side's precursor stage, the way a quotation precedes a sales order.
    `created_by` (from _Document) is the requester; supplier is optional at
    request time and can be chosen when converting to a PO."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CONVERTED = "converted", "Converted"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30)
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.PROTECT, related_name="purchase_requests",
        null=True, blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    request_date = models.DateField(auto_now_add=True)
    expected_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Who approved or rejected the request",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("company", "number")
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class PurchaseRequestItem(_LineItem):
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, related_name="+", null=True, blank=True)
