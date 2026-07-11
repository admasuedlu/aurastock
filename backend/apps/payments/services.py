from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.sales.models import Invoice
from apps.sales.services import record_invoice_payment

from .models import PaymentIntent
from .providers import get_provider


def create_payment_intent(*, invoice, method, amount=None, provider_name="sandbox", user=None) -> PaymentIntent:
    if invoice.status not in (Invoice.Status.CONFIRMED, Invoice.Status.PARTIALLY_PAID):
        raise ValidationError("Only a confirmed invoice with a balance can be paid online.")
    balance = invoice.balance_due
    amount = balance if amount is None else Decimal(str(amount))
    if amount <= 0:
        raise ValidationError("Payment amount must be positive.")
    if amount > balance:
        raise ValidationError("Payment amount exceeds the invoice balance.")

    provider = get_provider(provider_name)  # validates the provider name
    intent = PaymentIntent.objects.create(
        company=invoice.company, invoice=invoice, provider=provider_name,
        method=method, amount=amount, created_by=user,
    )
    checkout = provider.create_checkout(intent)
    intent.checkout_url = checkout["checkout_url"]
    intent.external_reference = checkout["external_reference"]
    intent.save(update_fields=["checkout_url", "external_reference"])
    return intent


@transaction.atomic
def confirm_payment_intent(intent: PaymentIntent, *, external_reference="") -> PaymentIntent:
    """Mark an intent paid and record the real SalesPayment. Idempotent -- a
    provider that delivers the same webhook twice won't double-charge."""
    if intent.status == PaymentIntent.Status.SUCCEEDED:
        return intent
    if intent.status != PaymentIntent.Status.PENDING:
        raise ValidationError(f"A {intent.get_status_display().lower()} payment can't be confirmed.")

    payment = record_invoice_payment(
        intent.invoice, amount=intent.amount, method=intent.method,
        reference=intent.reference, user=intent.created_by,
    )
    intent.status = PaymentIntent.Status.SUCCEEDED
    intent.sales_payment = payment
    if external_reference:
        intent.external_reference = external_reference
    intent.save(update_fields=["status", "sales_payment", "external_reference", "updated_at"])
    return intent


def handle_webhook(provider_name: str, headers, body: bytes) -> PaymentIntent:
    """Entry point a live provider POSTs to. Verifies the signature, finds the
    intent by our reference, and confirms or fails it."""
    parsed = get_provider(provider_name).parse_webhook(headers, body)
    try:
        intent = PaymentIntent.objects.select_related("invoice").get(reference=parsed["reference"])
    except PaymentIntent.DoesNotExist:
        raise ValidationError("Unknown payment reference.")

    if parsed["status"] == "succeeded":
        return confirm_payment_intent(intent, external_reference=parsed.get("external_reference", ""))
    if parsed["status"] == "failed" and intent.status == PaymentIntent.Status.PENDING:
        intent.status = PaymentIntent.Status.FAILED
        intent.save(update_fields=["status", "updated_at"])
    return intent
