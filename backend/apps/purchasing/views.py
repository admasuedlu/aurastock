from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.accounting import services as accounting_services
from apps.core.numbering import next_value
from apps.core.viewsets import CompanyScopedViewSet
from apps.suppliers.models import Supplier

from .models import GoodsReceipt, PurchaseOrder, PurchaseOrderItem, PurchaseRequest
from .serializers import (
    GoodsReceiptSerializer,
    PurchaseOrderSerializer,
    PurchasePaymentSerializer,
    PurchaseRequestSerializer,
)


class PurchaseOrderViewSet(CompanyScopedViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier").prefetch_related("items").all()
    serializer_class = PurchaseOrderSerializer
    permission_module = "purchases"
    filterset_fields = ["supplier", "status"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Marks a draft PO as sent to the supplier -- the transition that
        makes it visible in the supplier portal (mirrors quotation send)."""
        order = self.get_object()
        if order.status != PurchaseOrder.Status.DRAFT:
            raise DRFValidationError("Only a draft purchase order can be sent.")
        order.status = PurchaseOrder.Status.SENT
        order.save(update_fields=["status", "updated_at"])
        return Response(PurchaseOrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        order = self.get_object()
        serializer = PurchasePaymentSerializer(data={**request.data, "purchase_order": order.id})
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        if amount <= 0:
            raise DRFValidationError("Payment amount must be positive.")
        if order.amount_paid + amount > order.total:
            raise DRFValidationError("Payment exceeds the outstanding balance.")

        payment = serializer.save(company=order.company, created_by=request.user)
        order.amount_paid += amount
        order.save(update_fields=["amount_paid", "updated_at"])
        accounting_services.record_purchase_payment(payment, order)
        return Response(PurchaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class GoodsReceiptViewSet(CompanyScopedViewSet):
    queryset = GoodsReceipt.objects.select_related("purchase_order", "warehouse").prefetch_related("items").all()
    serializer_class = GoodsReceiptSerializer
    permission_module = "purchases"
    # Receiving goods against an existing PO is a "change" to the purchasing
    # flow, not authoring a new document -- so it needs purchases.change
    # (which a Warehouse Manager holds), distinct from purchases.add used to
    # create/send purchase orders.
    permission_action_map = {"create": "change"}
    filterset_fields = ["purchase_order", "warehouse"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)


class PurchaseRequestViewSet(CompanyScopedViewSet):
    queryset = PurchaseRequest.objects.select_related(
        "supplier", "created_by", "approved_by",
    ).prefetch_related("items").all()
    serializer_class = PurchaseRequestSerializer
    permission_module = "purchases"
    # Approving/rejecting a request needs the dedicated `approve` permission
    # (Owner/Admin/Procurement Officer), not just general purchase-write access.
    permission_action_map = {"approve": "approve", "reject": "approve"}
    filterset_fields = ["supplier", "status"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Draft -> submitted: sends the request for approval."""
        purchase_request = self.get_object()
        if purchase_request.status != PurchaseRequest.Status.DRAFT:
            raise DRFValidationError("Only a draft request can be submitted for approval.")
        if not purchase_request.items.exists():
            raise DRFValidationError("Cannot submit a request with no line items.")
        purchase_request.status = PurchaseRequest.Status.SUBMITTED
        purchase_request.save(update_fields=["status", "updated_at"])
        return Response(PurchaseRequestSerializer(purchase_request).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Submitted -> approved, recording who approved and when."""
        purchase_request = self.get_object()
        if purchase_request.status != PurchaseRequest.Status.SUBMITTED:
            raise DRFValidationError("Only a submitted request can be approved.")
        purchase_request.status = PurchaseRequest.Status.APPROVED
        purchase_request.approved_by = request.user
        purchase_request.approved_at = timezone.now()
        purchase_request.rejection_reason = ""
        purchase_request.save(update_fields=["status", "approved_by", "approved_at", "rejection_reason", "updated_at"])
        return Response(PurchaseRequestSerializer(purchase_request).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Submitted -> rejected, capturing the reason and who rejected it."""
        purchase_request = self.get_object()
        if purchase_request.status != PurchaseRequest.Status.SUBMITTED:
            raise DRFValidationError("Only a submitted request can be rejected.")
        purchase_request.status = PurchaseRequest.Status.REJECTED
        purchase_request.approved_by = request.user
        purchase_request.approved_at = timezone.now()
        purchase_request.rejection_reason = request.data.get("reason", "")
        purchase_request.save(update_fields=["status", "approved_by", "approved_at", "rejection_reason", "updated_at"])
        return Response(PurchaseRequestSerializer(purchase_request).data)

    @action(detail=True, methods=["post"], url_path="convert-to-po")
    @transaction.atomic
    def convert_to_po(self, request, pk=None):
        """Approved -> a real purchase order. Copies the line items, links back
        via PurchaseOrder.purchase_request, and locks the request as converted.
        A PO needs a supplier; use the request's if it has one, otherwise the
        caller supplies it here."""
        purchase_request = self.get_object()
        if purchase_request.status != PurchaseRequest.Status.APPROVED:
            raise DRFValidationError("Only an approved request can be converted to a purchase order.")

        request_items = list(purchase_request.items.select_related("product", "variant").all())
        if not request_items:
            raise DRFValidationError("Request has no line items to order.")

        supplier = purchase_request.supplier
        supplier_id = request.data.get("supplier")
        if supplier_id:
            try:
                supplier = Supplier.objects.get(company=purchase_request.company, pk=supplier_id)
            except (Supplier.DoesNotExist, ValueError, DjangoValidationError):
                raise DRFValidationError({"supplier": "No supplier with that id."})
        if supplier is None:
            raise DRFValidationError({"supplier": "This request has no supplier; provide one to order from."})

        order = PurchaseOrder.objects.create(
            company=purchase_request.company, supplier=supplier, purchase_request=purchase_request,
            created_by=request.user, notes=purchase_request.notes, expected_date=purchase_request.expected_date,
            number=next_value(purchase_request.company, "purchase_order", default_prefix="PO-"),
        )
        order_items = [
            PurchaseOrderItem(
                company=purchase_request.company, purchase_order=order, product=item.product, variant=item.variant,
                quantity=item.quantity, unit_price=item.unit_price,
                discount_percent=item.discount_percent, tax_percent=item.tax_percent,
            )
            for item in request_items
        ]
        PurchaseOrderItem.objects.bulk_create(order_items)
        order.recalculate_totals(order_items)
        order.save(update_fields=["subtotal", "discount_total", "tax_total", "total"])

        purchase_request.status = PurchaseRequest.Status.CONVERTED
        purchase_request.save(update_fields=["status", "updated_at"])

        return Response(PurchaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)
