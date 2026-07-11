from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.accounting import services as accounting_services
from apps.core.numbering import next_value
from apps.core.viewsets import CompanyScopedViewSet
from apps.inventory.models import Warehouse
from apps.inventory.services import stock_out
from apps.sales import services as sales_services

from .models import Invoice, InvoiceItem, Quotation, SalesOrder, SalesOrderItem, SalesPayment
from .serializers import (
    InvoiceSerializer,
    QuotationSerializer,
    SalesOrderSerializer,
    SalesPaymentSerializer,
)

_UNCONVERTIBLE_QUOTATION_STATUSES = (Quotation.Status.CONVERTED, Quotation.Status.REJECTED, Quotation.Status.EXPIRED)


class QuotationViewSet(CompanyScopedViewSet):
    queryset = Quotation.objects.select_related("customer").prefetch_related("items").all()
    serializer_class = QuotationSerializer
    permission_module = "sales"
    filterset_fields = ["customer", "status"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Marks a draft quotation as sent -- the transition that makes it
        visible in the customer portal. Quotations have had a `sent` status
        since Phase 2, but until the portal nothing could move them into it."""
        quotation = self.get_object()
        if quotation.status != Quotation.Status.DRAFT:
            raise DRFValidationError("Only a draft quotation can be sent.")
        quotation.status = Quotation.Status.SENT
        quotation.save(update_fields=["status", "updated_at"])
        return Response(QuotationSerializer(quotation).data)

    @action(detail=True, methods=["post"], url_path="convert-to-order")
    @transaction.atomic
    def convert_to_order(self, request, pk=None):
        quotation = self.get_object()
        if quotation.status in _UNCONVERTIBLE_QUOTATION_STATUSES:
            raise DRFValidationError(f"A {quotation.get_status_display().lower()} quotation cannot be converted.")

        quotation_items = list(quotation.items.select_related("product", "variant").all())
        if not quotation_items:
            raise DRFValidationError("Quotation has no line items to convert.")

        order = SalesOrder.objects.create(
            company=quotation.company, customer=quotation.customer, quotation=quotation,
            created_by=request.user,
            number=next_value(quotation.company, "sales_order", default_prefix="SO-"),
        )

        order_items = [
            SalesOrderItem(
                company=quotation.company, sales_order=order, product=item.product, variant=item.variant,
                quantity=item.quantity, unit_price=item.unit_price,
                discount_percent=item.discount_percent, tax_percent=item.tax_percent,
            )
            for item in quotation_items
        ]
        SalesOrderItem.objects.bulk_create(order_items)
        order.recalculate_totals(order_items)
        order.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])

        quotation.status = Quotation.Status.CONVERTED
        quotation.save(update_fields=["status", "updated_at"])

        return Response(SalesOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class SalesOrderViewSet(CompanyScopedViewSet):
    queryset = SalesOrder.objects.select_related("customer", "quotation").prefetch_related("items").all()
    serializer_class = SalesOrderSerializer
    permission_module = "sales"
    filterset_fields = ["customer", "status"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="convert-to-invoice")
    @transaction.atomic
    def convert_to_invoice(self, request, pk=None):
        """Creates a draft invoice from a sales order, copying line items and
        linking back via Invoice.sales_order. Supports partial invoicing: pass
        `items: [{sales_order_item, quantity}, ...]` to invoice specific
        amounts, or omit it to invoice every line's full outstanding quantity.
        Each SO line tracks quantity_invoiced (like a PO tracks
        quantity_received), so an order can be billed across several invoices;
        the order goes CONFIRMED while anything is still outstanding and
        FULFILLED once every line is fully invoiced. An invoice needs a
        warehouse (to deduct stock from on confirm) that the order doesn't
        carry, so the caller supplies it."""
        order = self.get_object()
        if order.status == SalesOrder.Status.CANCELLED:
            raise DRFValidationError("A cancelled sales order cannot be invoiced.")

        order_items = {str(i.id): i for i in order.items.select_related("product", "variant").all()}
        if not order_items:
            raise DRFValidationError("Sales order has no line items to invoice.")

        requested = request.data.get("items")
        if requested:
            to_invoice = []
            for entry in requested:
                item = order_items.get(str(entry.get("sales_order_item")))
                if item is None:
                    raise DRFValidationError({"items": "A line does not belong to this sales order."})
                try:
                    qty = Decimal(str(entry.get("quantity")))
                except (InvalidOperation, TypeError):
                    raise DRFValidationError({"items": f"Invalid quantity for {item.product.name}."})
                if qty <= 0:
                    continue
                if qty > item.quantity_outstanding:
                    raise DRFValidationError({
                        "items": f"Cannot invoice {qty} of {item.product.name}: only "
                                 f"{item.quantity_outstanding} outstanding."
                    })
                to_invoice.append((item, qty))
        else:
            to_invoice = [
                (item, item.quantity_outstanding)
                for item in order_items.values() if item.quantity_outstanding > 0
            ]

        if not to_invoice:
            raise DRFValidationError("Nothing left to invoice on this sales order.")

        warehouse_id = request.data.get("warehouse")
        if not warehouse_id:
            raise DRFValidationError({"warehouse": "This field is required."})
        try:
            warehouse = Warehouse.objects.get(company=order.company, pk=warehouse_id)
        except (Warehouse.DoesNotExist, ValueError, DjangoValidationError):
            raise DRFValidationError({"warehouse": "No warehouse with that id."})

        invoice = Invoice.objects.create(
            company=order.company, customer=order.customer, sales_order=order, warehouse=warehouse,
            created_by=request.user, notes=order.notes, due_date=request.data.get("due_date") or None,
            number=next_value(order.company, "invoice", default_prefix="INV-"),
        )
        invoice_items = [
            InvoiceItem(
                company=order.company, invoice=invoice, product=item.product, variant=item.variant,
                quantity=qty, unit_price=item.unit_price,
                discount_percent=item.discount_percent, tax_percent=item.tax_percent,
            )
            for item, qty in to_invoice
        ]
        InvoiceItem.objects.bulk_create(invoice_items)
        invoice.recalculate_totals(invoice_items)
        invoice.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])

        for item, qty in to_invoice:
            item.quantity_invoiced += qty
            item.save(update_fields=["quantity_invoiced"])

        # Fully invoiced (every line's outstanding is zero) -> FULFILLED;
        # otherwise still CONFIRMED with more to bill later. Check order_items
        # (freshly loaded and mutated above), not order.items.all() -- the
        # latter is the prefetched cache from get_object() and still holds the
        # pre-increment quantities.
        if all(i.quantity_outstanding <= 0 for i in order_items.values()):
            order.status = SalesOrder.Status.FULFILLED
        else:
            order.status = SalesOrder.Status.CONFIRMED
        order.save(update_fields=["status", "updated_at"])

        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceViewSet(CompanyScopedViewSet):
    queryset = Invoice.objects.select_related("customer", "warehouse", "sales_order").prefetch_related("items", "payments").all()
    serializer_class = InvoiceSerializer
    permission_module = "sales"
    filterset_fields = ["customer", "status", "warehouse"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            raise DRFValidationError("Only draft invoices can be confirmed.")

        cogs_amount = Decimal("0")
        try:
            for item in invoice.items.select_related("product", "variant").all():
                movement = stock_out(
                    company=invoice.company,
                    warehouse=invoice.warehouse,
                    product=item.product,
                    variant=item.variant,
                    quantity=item.quantity,
                    reference=invoice.number,
                    reason="Invoice confirmed",
                    user=request.user,
                )
                cogs_amount += movement.quantity * movement.unit_cost
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages if hasattr(exc, "messages") else str(exc))

        invoice.status = Invoice.Status.CONFIRMED
        invoice.save(update_fields=["status", "updated_at"])
        accounting_services.record_invoice_confirmed(invoice, cogs_amount=cogs_amount)
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        invoice = self.get_object()
        serializer = SalesPaymentSerializer(data={**request.data, "invoice": invoice.id})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            sales_services.record_invoice_payment(
                invoice, amount=data["amount"], method=data.get("method", "cash"),
                reference=data.get("reference", ""), user=request.user,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages if hasattr(exc, "messages") else str(exc))
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)
