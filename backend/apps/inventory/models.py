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


class StockMovement(CompanyScopedModel):
    class MovementType(models.TextChoices):
        STOCK_IN = "stock_in", "Stock in"
        STOCK_OUT = "stock_out", "Stock out"
        TRANSFER_OUT = "transfer_out", "Transfer out"
        TRANSFER_IN = "transfer_in", "Transfer in"
        ADJUSTMENT_ADD = "adjustment_add", "Adjustment (add)"
        ADJUSTMENT_REMOVE = "adjustment_remove", "Adjustment (remove)"

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="movements")
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
