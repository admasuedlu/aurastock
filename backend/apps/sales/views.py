from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.core.viewsets import CompanyScopedViewSet
from apps.inventory.services import stock_out

from .models import Invoice, Quotation, SalesOrder, SalesPayment
from .serializers import (
    InvoiceSerializer,
    QuotationSerializer,
    SalesOrderSerializer,
    SalesPaymentSerializer,
)


class QuotationViewSet(CompanyScopedViewSet):
    queryset = Quotation.objects.select_related("customer").prefetch_related("items").all()
    serializer_class = QuotationSerializer
    filterset_fields = ["customer", "status"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)


class SalesOrderViewSet(CompanyScopedViewSet):
    queryset = SalesOrder.objects.select_related("customer", "quotation").prefetch_related("items").all()
    serializer_class = SalesOrderSerializer
    filterset_fields = ["customer", "status"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)


class InvoiceViewSet(CompanyScopedViewSet):
    queryset = Invoice.objects.select_related("customer", "warehouse", "sales_order").prefetch_related("items", "payments").all()
    serializer_class = InvoiceSerializer
    filterset_fields = ["customer", "status", "warehouse"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            raise DRFValidationError("Only draft invoices can be confirmed.")

        try:
            for item in invoice.items.select_related("product", "variant").all():
                stock_out(
                    company=invoice.company,
                    warehouse=invoice.warehouse,
                    product=item.product,
                    variant=item.variant,
                    quantity=item.quantity,
                    reference=invoice.number,
                    reason="Invoice confirmed",
                    user=request.user,
                )
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages if hasattr(exc, "messages") else str(exc))

        invoice.status = Invoice.Status.CONFIRMED
        invoice.save(update_fields=["status", "updated_at"])
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"], url_path="record-payment")
    @transaction.atomic
    def record_payment(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status not in (Invoice.Status.CONFIRMED, Invoice.Status.PARTIALLY_PAID):
            raise DRFValidationError("Only confirmed invoices can receive payments.")

        serializer = SalesPaymentSerializer(data={**request.data, "invoice": invoice.id})
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        if amount <= 0:
            raise DRFValidationError("Payment amount must be positive.")
        if invoice.amount_paid + amount > invoice.total:
            raise DRFValidationError("Payment exceeds the outstanding balance.")

        serializer.save(company=invoice.company, created_by=request.user)
        invoice.amount_paid += amount
        invoice.status = (
            Invoice.Status.PAID if invoice.amount_paid >= invoice.total else Invoice.Status.PARTIALLY_PAID
        )
        invoice.save(update_fields=["amount_paid", "status", "updated_at"])
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)
