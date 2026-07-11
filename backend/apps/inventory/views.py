from datetime import date, timedelta
from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.viewsets import CompanyScopedViewSet
from apps.tenants.limits import enforce_plan_limit

from . import services
from .models import Batch, StockItem, StockMovement, Warehouse
from .serializers import (
    AssembleSerializer,
    BatchSerializer,
    StockAdjustmentSerializer,
    StockInSerializer,
    StockItemSerializer,
    StockMovementSerializer,
    StockOutSerializer,
    StockTransferSerializer,
    WarehouseSerializer,
)


def _broadcast_stock_change(company_id, stock_item):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"company-{company_id}-inventory",
        {
            "type": "stock.update",
            "data": StockItemSerializer(stock_item).data,
        },
    )


class WarehouseViewSet(CompanyScopedViewSet):
    queryset = Warehouse.objects.select_related("branch").all()
    serializer_class = WarehouseSerializer
    filterset_fields = ["branch", "is_active"]
    search_fields = ["name", "code"]

    def perform_create(self, serializer):
        try:
            enforce_plan_limit(self.request.user.company, "warehouses")
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages)
        super().perform_create(serializer)


class StockItemViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = StockItem.objects.select_related("product", "warehouse", "variant").all()
    serializer_class = StockItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["warehouse", "product", "variant"]
    search_fields = ["product__name", "product__sku"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(company_id=user.company_id)
        return qs

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        low_items = [item for item in self.filter_queryset(self.get_queryset())
                     if item.quantity_on_hand <= item.product.reorder_level]
        page = self.paginate_queryset(low_items)
        serializer = self.get_serializer(page if page is not None else low_items, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)


class StockMovementViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = StockMovement.objects.select_related("product", "warehouse", "created_by", "batch").all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["warehouse", "product", "movement_type"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(company_id=user.company_id)
        return qs


class BatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Lot/batch records with their total on-hand quantity across warehouses,
    plus an `expiring` report for stock nearing (or past) its expiry date."""

    serializer_class = BatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["product"]

    def get_queryset(self):
        return (
            Batch.objects.filter(company_id=self.request.user.company_id)
            .select_related("product")
            .annotate(quantity_on_hand=Coalesce(
                Sum("stocks__quantity_on_hand"),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            ))
        )

    @action(detail=False)
    def expiring(self, request):
        """Batches still on hand whose expiry is within `days` (default 30),
        including already-expired ones -- soonest first."""
        days = int(request.query_params.get("days", 30))
        cutoff = date.today() + timedelta(days=days)
        batches = (
            self.get_queryset()
            .filter(expiry_date__isnull=False, expiry_date__lte=cutoff, quantity_on_hand__gt=0)
            .order_by("expiry_date")
        )
        page = self.paginate_queryset(batches)
        serializer = self.get_serializer(page if page is not None else batches, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)


class _StockActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None
    service_fn = None

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            movement = self.service_fn(
                company=request.user.company, user=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages if hasattr(exc, "messages") else str(exc))

        stock_item = StockItem.objects.get(
            company=request.user.company, warehouse=movement.warehouse,
            product=movement.product, variant=movement.variant,
        )
        _broadcast_stock_change(request.user.company_id, stock_item)
        return Response(StockMovementSerializer(movement).data, status=201)


class StockInView(_StockActionView):
    serializer_class = StockInSerializer
    service_fn = staticmethod(services.stock_in)


class StockOutView(_StockActionView):
    serializer_class = StockOutSerializer
    service_fn = staticmethod(services.stock_out)


class StockAdjustmentView(_StockActionView):
    serializer_class = StockAdjustmentSerializer
    service_fn = staticmethod(services.adjust_stock)


class AssembleView(_StockActionView):
    """Kitting: consume a bundle's components and produce bundle stock. Returns
    the bundle's stock-in movement (so the shared base broadcasts the bundle's
    new on-hand)."""

    serializer_class = AssembleSerializer
    service_fn = staticmethod(services.assemble_bundle)


class StockTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = StockTransferSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            movement = services.transfer_stock(
                company=request.user.company, user=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages if hasattr(exc, "messages") else str(exc))

        for warehouse in (movement.warehouse, movement.related_warehouse):
            stock_item = StockItem.objects.get(
                company=request.user.company, warehouse=warehouse,
                product=movement.product, variant=movement.variant,
            )
            _broadcast_stock_change(request.user.company_id, stock_item)
        return Response(StockMovementSerializer(movement).data, status=201)
