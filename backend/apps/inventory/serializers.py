from decimal import Decimal

from rest_framework import serializers

from apps.products.models import Product, ProductVariant

from .models import Batch, StockItem, StockMovement, Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "branch", "name", "code", "address", "is_active"]


class StockItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    available_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    reorder_level = serializers.DecimalField(source="product.reorder_level", max_digits=12,
                                              decimal_places=2, read_only=True)
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = StockItem
        fields = [
            "id", "warehouse", "warehouse_name", "product", "product_name", "product_sku",
            "variant", "quantity_on_hand", "reserved_quantity", "incoming_quantity",
            "damaged_quantity", "available_quantity", "average_cost", "reorder_level", "is_low_stock",
        ]

    def get_is_low_stock(self, obj):
        return obj.quantity_on_hand <= obj.product.reorder_level


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True, default=None)

    class Meta:
        model = StockMovement
        fields = [
            "id", "warehouse", "warehouse_name", "related_warehouse", "product", "product_name",
            "variant", "movement_type", "quantity", "unit_cost", "reference", "reason",
            "batch", "batch_number", "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = fields


class BatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    # Populated by the viewset's annotation (total on-hand across warehouses).
    quantity_on_hand = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = Batch
        fields = ["id", "product", "product_name", "product_sku", "batch_number",
                  "expiry_date", "quantity_on_hand"]


class _CompanyScopedActionSerializer(serializers.Serializer):
    """Base for stock-operation input serializers: scopes FK choice fields
    to the requesting user's company so cross-tenant IDs are rejected."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = self.context["request"].user.company
        for field_name, model in self._scoped_fields().items():
            if field_name in self.fields:
                self.fields[field_name].queryset = model.objects.filter(company=company)

    def _scoped_fields(self):
        return {}


class StockInSerializer(_CompanyScopedActionSerializer):
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.none())
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.none(), required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit_cost = serializers.DecimalField(max_digits=14, decimal_places=4, default=0)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
    batch_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)

    def _scoped_fields(self):
        return {"warehouse": Warehouse, "product": Product, "variant": ProductVariant}


class StockOutSerializer(_CompanyScopedActionSerializer):
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.none())
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.none(), required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def _scoped_fields(self):
        return {"warehouse": Warehouse, "product": Product, "variant": ProductVariant}


class StockTransferSerializer(_CompanyScopedActionSerializer):
    from_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    to_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.none())
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.none(), required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def _scoped_fields(self):
        return {"from_warehouse": Warehouse, "to_warehouse": Warehouse, "product": Product, "variant": ProductVariant}


class StockAdjustmentSerializer(_CompanyScopedActionSerializer):
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.none())
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.none())
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.none(), required=False, allow_null=True)
    quantity_delta = serializers.DecimalField(max_digits=14, decimal_places=3)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
    batch_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)

    def _scoped_fields(self):
        return {"warehouse": Warehouse, "product": Product, "variant": ProductVariant}
