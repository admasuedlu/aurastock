from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.core.viewsets import CompanyScopedViewSet
from apps.inventory.models import StockMovement
from apps.inventory.services import stock_in

from .models import POSSession, POSTransaction
from .serializers import POSSessionSerializer, POSTransactionSerializer


class POSSessionViewSet(CompanyScopedViewSet):
    queryset = POSSession.objects.select_related("warehouse", "cashier").all()
    serializer_class = POSSessionSerializer
    filterset_fields = ["warehouse", "status"]

    def perform_create(self, serializer):
        user = self.request.user
        if POSSession.objects.filter(company=user.company, cashier=user, status=POSSession.Status.OPEN).exists():
            raise DRFValidationError("You already have an open till session. Close it before opening a new one.")
        serializer.save(company=user.company, cashier=user)

    @action(detail=False, methods=["get"])
    def current(self, request):
        session = self.get_queryset().filter(cashier=request.user, status=POSSession.Status.OPEN).first()
        if session is None:
            return Response(None)
        return Response(POSSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def close(self, request, pk=None):
        session = self.get_object()
        if session.status != POSSession.Status.OPEN:
            raise DRFValidationError("This session is already closed.")

        closing_cash = request.data.get("closing_cash")
        if closing_cash is None:
            raise DRFValidationError("closing_cash is required.")

        cash_sales = session.transactions.filter(
            status=POSTransaction.Status.COMPLETED, payment_method="cash",
        ).aggregate(total=Sum("total"))["total"] or Decimal("0")
        expected_cash = session.opening_cash + cash_sales

        session.closing_cash = Decimal(str(closing_cash))
        session.expected_cash = expected_cash
        session.cash_variance = session.closing_cash - expected_cash
        session.status = POSSession.Status.CLOSED
        session.closed_at = timezone.now()
        session.save(update_fields=["closing_cash", "expected_cash", "cash_variance", "status", "closed_at"])
        return Response(POSSessionSerializer(session).data)


class POSTransactionViewSet(CompanyScopedViewSet):
    queryset = POSTransaction.objects.select_related("session", "customer").prefetch_related("items").all()
    serializer_class = POSTransactionSerializer
    filterset_fields = ["session", "customer", "status"]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def refund(self, request, pk=None):
        pos_transaction = self.get_object()
        if pos_transaction.status != POSTransaction.Status.COMPLETED:
            raise DRFValidationError("Only completed transactions can be refunded.")

        for item in pos_transaction.items.select_related("product", "variant").all():
            original_movement = StockMovement.objects.filter(
                company=pos_transaction.company, reference=pos_transaction.number,
                product=item.product, variant=item.variant,
                movement_type=StockMovement.MovementType.STOCK_OUT,
            ).order_by("-created_at").first()
            # Restore stock at the cost basis it left at, not today's average, so
            # refunding a sale doesn't dilute the remaining stock's average cost.
            unit_cost = original_movement.unit_cost if original_movement else Decimal("0")

            stock_in(
                company=pos_transaction.company, warehouse=pos_transaction.session.warehouse,
                product=item.product, variant=item.variant, quantity=item.quantity,
                unit_cost=unit_cost, reference=pos_transaction.number,
                reason="POS refund", user=request.user,
            )

        pos_transaction.status = POSTransaction.Status.REFUNDED
        pos_transaction.save(update_fields=["status", "updated_at"])
        return Response(POSTransactionSerializer(pos_transaction).data)
