from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel


class Warehouse(CompanyScopedModel):
    branch = models.ForeignKey(
        "tenants.Branch", on_delete=models.CASCADE, related_name="warehouses", null=True, blank=True,
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockItem(CompanyScopedModel):
    """Current on-hand snapshot per (warehouse, product[, variant]). The
    source of truth for history is `StockMovement`; this table is a
    maintained aggregate for fast availability lookups."""

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="stock_items")
    variant = models.ForeignKey(
        "products.ProductVariant", on_delete=models.CASCADE, related_name="stock_items", null=True, blank=True,
    )
    quantity_on_hand = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    reserved_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    incoming_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    damaged_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    average_cost = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))

    class Meta:
        unique_together = ("company", "warehouse", "product", "variant")

    def __str__(self):
        variant_part = f"/{self.variant.sku}" if self.variant_id else ""
        return f"{self.product.sku}{variant_part} @ {self.warehouse.code}"

    @property
    def available_quantity(self):
        return self.quantity_on_hand - self.reserved_quantity


class Batch(CompanyScopedModel):
    """A lot/batch of a product, optionally with an expiry date. Identified by
    its number within a product; created on receipt of batch-tracked goods.
    Per-warehouse on-hand quantity lives in BatchStock."""

    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("company", "product", "batch_number")
        ordering = ["expiry_date", "batch_number"]

    def __str__(self):
        return f"{self.product.sku} · {self.batch_number}"


class BatchStock(CompanyScopedModel):
    """On-hand quantity of a specific batch in a specific warehouse. The sum of
    a product's BatchStock in a warehouse mirrors that warehouse's StockItem
    quantity_on_hand for batch-tracked products; it just says *which* batches
    make it up, for traceability and first-expiry-first-out picking."""

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="batch_stocks")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="batch_stocks")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="stocks")
    quantity_on_hand = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))

    class Meta:
        unique_together = ("company", "warehouse", "product", "batch")

    def __str__(self):
        return f"{self.batch.batch_number} @ {self.warehouse.code}: {self.quantity_on_hand}"


class StockMovement(CompanyScopedModel):
    class MovementType(models.TextChoices):
        STOCK_IN = "stock_in", "Stock in"
        STOCK_OUT = "stock_out", "Stock out"
        TRANSFER_OUT = "transfer_out", "Transfer out"
        TRANSFER_IN = "transfer_in", "Transfer in"
        ADJUSTMENT_ADD = "adjustment_add", "Adjustment (add)"
        ADJUSTMENT_REMOVE = "adjustment_remove", "Adjustment (remove)"

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="movements")
    batch = models.ForeignKey(
        Batch, on_delete=models.SET_NULL, related_name="movements", null=True, blank=True,
        help_text="Set when the movement is entirely one batch (blank if it spanned several via FEFO)",
    )
    related_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, related_name="related_movements", null=True, blank=True,
        help_text="Other side of a transfer",
    )
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="movements")
    variant = models.ForeignKey(
        "products.ProductVariant", on_delete=models.CASCADE, related_name="movements", null=True, blank=True,
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    reference = models.CharField(max_length=100, blank=True, help_text="PO/SO/GRN number etc.")
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="stock_movements", null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "product", "warehouse"])]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} {self.product.sku}"
