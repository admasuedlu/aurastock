from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel
from apps.sales.models import PaymentMethod, _Document, _LineItem


class POSSession(CompanyScopedModel):
    """A cashier's shift at a till: opened with a starting cash float,
    closed with a counted cash amount so variance can be reconciled."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="pos_sessions")
    cashier = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="pos_sessions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    opening_cash = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    closing_cash = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    expected_cash = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cash_variance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self):
        return f"Session {self.id} ({self.cashier})"


class POSTransaction(_Document):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        REFUNDED = "refunded", "Refunded"

    number = models.CharField(max_length=30)
    session = models.ForeignKey(POSSession, on_delete=models.PROTECT, related_name="transactions")
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.SET_NULL, related_name="pos_transactions", null=True, blank=True,
        help_text="Null for a walk-in customer",
    )
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    amount_tendered = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)

    class Meta:
        unique_together = ("company", "number")
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    @property
    def change_due(self) -> Decimal:
        return max(self.amount_tendered - self.total, Decimal("0"))


class POSTransactionItem(_LineItem):
    transaction = models.ForeignKey(POSTransaction, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="+")
    variant = models.ForeignKey("products.ProductVariant", on_delete=models.PROTECT, related_name="+", null=True, blank=True)
