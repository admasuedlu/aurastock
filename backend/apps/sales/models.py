from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    BANK_TRANSFER = "bank_transfer", "Bank transfer"
    TELEBIRR = "telebirr", "Telebirr"
    CBE_PAY = "cbe_pay", "CBE Pay"
    MPESA = "mpesa", "M-Pesa"
    AMOLE = "amole", "Amole"
    OTHER = "other", "Other"


class _LineItem(CompanyScopedModel):
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15"))

    class Meta:
        abstract = True

    @property
    def line_subtotal(self) -> Decimal:
        return self.quantity * self.unit_price * (Decimal("1") - self.discount_percent / Decimal("100"))

    @property
    def line_tax(self) -> Decimal:
        return self.line_subtotal * self.tax_percent / Decimal("100")

    @property
    def line_total(self) -> Decimal:
        return self.line_subtotal + self.line_tax


class _Document(CompanyScopedModel):
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    discount_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    tax_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )

    class Meta:
        abstract = True

    def recalculate_totals(self, items):
        gross = sum((i.quantity * i.unit_price for i in items), Decimal("0"))
        self.subtotal = sum((i.line_subtotal for i in items), Decimal("0"))
        self.discount_total = gross - self.subtotal
        self.tax_total = sum((i.line_tax for i in items), Decimal("0"))
        self.total = self.subtotal + self.tax_total


class Quotation(_Document):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CONVERTED = "converted", "Converted"

    number = models.CharField(max_length=30)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="quotations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    issue_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("company", "number")
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class QuotationItem(_LineItem):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, related_name="+", null=True, blank=True)


class SalesOrder(_Document):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        FULFILLED = "fulfilled", "Fulfilled"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="sales_orders")
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, related_name="sales_orders", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    order_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "number")
        ordering = ["-created_at"]

    def __str__(self):
        return self.number


class SalesOrderItem(_LineItem):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, related_name="+", null=True, blank=True)
    quantity_invoiced = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))

    @property
    def quantity_outstanding(self) -> Decimal:
        return self.quantity - self.quantity_invoiced


class Invoice(_Document):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        PARTIALLY_PAID = "partially_paid", "Partially paid"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="invoices")
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.SET_NULL, related_name="invoices", null=True, blank=True)
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="invoices")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = ("company", "number")
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    @property
    def balance_due(self) -> Decimal:
        return self.total - self.amount_paid


class InvoiceItem(_LineItem):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, related_name="+", null=True, blank=True)


class SalesPayment(CompanyScopedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-paid_at"]
