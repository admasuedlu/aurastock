from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.core.viewsets import CompanyScopedViewSet

from .models import GoodsReceipt, PurchaseOrder
from .serializers import GoodsReceiptSerializer, PurchaseOrderSerializer, PurchasePaymentSerializer


class PurchaseOrderViewSet(CompanyScopedViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier").prefetch_related("items").all()
    serializer_class = PurchaseOrderSerializer
    filterset_fields = ["supplier", "status"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

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

        serializer.save(company=order.company, created_by=request.user)
        order.amount_paid += amount
        order.save(update_fields=["amount_paid", "updated_at"])
        return Response(PurchaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class GoodsReceiptViewSet(CompanyScopedViewSet):
    queryset = GoodsReceipt.objects.select_related("purchase_order", "warehouse").prefetch_related("items").all()
    serializer_class = GoodsReceiptSerializer
    filterset_fields = ["purchase_order", "warehouse"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)
