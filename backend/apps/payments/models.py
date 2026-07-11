import secrets

from django.db import models

from apps.core.models import CompanyScopedModel
from apps.sales.models import PaymentMethod


def _new_reference():
    # Globally unique + unguessable: the webhook is unauthenticated and looks an
    # intent up by this reference across all tenants, so it can't be a per-company
    # counter, and it shouldn't be guessable.
    return secrets.token_urlsafe(16)


class PaymentIntent(CompanyScopedModel):
    """A request to collect a payment for an invoice through a gateway. The
    provider gives back a checkout URL for the payer; a later webhook (or, in
    the sandbox, a simulated callback) confirms it, which records the actual
    SalesPayment through the shared sales service."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    invoice = models.ForeignKey("sales.Invoice", on_delete=models.CASCADE, related_name="payment_intents")
    provider = models.CharField(max_length=30, default="sandbox")
    method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.TELEBIRR,
                              help_text="The payment method recorded on the resulting SalesPayment")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField(max_length=64, unique=True, default=_new_reference,
                                 help_text="Our globally-unique reference echoed back by the provider")
    external_reference = models.CharField(max_length=120, blank=True, help_text="Provider's transaction id")
    checkout_url = models.CharField(max_length=500, blank=True)
    sales_payment = models.ForeignKey("sales.SalesPayment", on_delete=models.SET_NULL, related_name="+",
                                      null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} ({self.status})"
