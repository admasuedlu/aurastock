from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounting import services as accounting_services

from .models import Invoice, SalesPayment


@transaction.atomic
def record_invoice_payment(invoice, *, amount: Decimal, method="cash", reference="", user=None) -> SalesPayment:
    """Records a payment against a confirmed invoice: creates the SalesPayment,
    advances amount_paid / status, and posts the ledger entry. Shared by the
    manual record-payment endpoint and the payment-gateway webhook, so both go
    through the same guards and accounting."""
    if invoice.status not in (Invoice.Status.CONFIRMED, Invoice.Status.PARTIALLY_PAID):
        raise ValidationError("Only confirmed invoices can receive payments.")
    if amount <= 0:
        raise ValidationError("Payment amount must be positive.")
    if invoice.amount_paid + amount > invoice.total:
        raise ValidationError("Payment exceeds the outstanding balance.")

    payment = SalesPayment.objects.create(
        company=invoice.company, invoice=invoice, amount=amount, method=method,
        reference=reference, created_by=user,
    )
    invoice.amount_paid += amount
    invoice.status = (
        Invoice.Status.PAID if invoice.amount_paid >= invoice.total else Invoice.Status.PARTIALLY_PAID
    )
    invoice.save(update_fields=["amount_paid", "status", "updated_at"])
    accounting_services.record_sales_payment(payment, invoice)
    return payment
