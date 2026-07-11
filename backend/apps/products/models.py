from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel


class Category(CompanyScopedModel):
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="subcategories", null=True, blank=True,
    )
    image = models.ImageField(upload_to="category_images/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "categories"
        unique_together = ("company", "parent", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Brand(CompanyScopedModel):
    name = models.CharField(max_length=150)
    logo = models.ImageField(upload_to="brand_logos/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class UnitOfMeasure(CompanyScopedModel):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    base_unit = models.ForeignKey(
        "self", on_delete=models.SET_NULL, related_name="derived_units", null=True, blank=True,
        help_text="e.g. carton's base unit is piece",
    )
    conversion_factor = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("1"),
        help_text="Multiply by this to convert 1 of this unit into base_unit",
    )

    class Meta:
        unique_together = ("company", "name")
        ordering = ["name"]

    def __str__(self):
        return self.symbol


class Product(CompanyScopedModel):
    class ProductType(models.TextChoices):
        SIMPLE = "simple", "Simple"
        VARIANT = "variant", "Has variants"
        SERVICE = "service", "Service"
        BUNDLE = "bundle", "Bundle"

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50)
    barcode = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name="products", null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name="products", null=True, blank=True)
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="products")
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.SIMPLE)

    cost_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    selling_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    tax_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15"),
                                            help_text="Ethiopian standard VAT is 15%")

    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    safety_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    track_serial = models.BooleanField(default=False)
    track_batch = models.BooleanField(default=False)
    track_expiry = models.BooleanField(default=False)

    image = models.ImageField(upload_to="product_images/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "sku")
        ordering = ["name"]
        indexes = [models.Index(fields=["company", "barcode"])]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class ProductVariant(CompanyScopedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=60)
    barcode = models.CharField(max_length=64, blank=True)
    attributes = models.JSONField(default=dict, blank=True, help_text='e.g. {"size": "M", "color": "Red"}')
    cost_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to="variant_images/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "sku")
        ordering = ["product", "sku"]

    def __str__(self):
        return self.sku

    def effective_selling_price(self):
        return self.selling_price if self.selling_price is not None else self.product.selling_price

    def effective_cost_price(self):
        return self.cost_price if self.cost_price is not None else self.product.cost_price


class BundleComponent(CompanyScopedModel):
    """One line of a bundle/kit's bill of materials: `quantity` units of
    `component` go into one `bundle`. Assembling the bundle (see
    apps.inventory.services.assemble_bundle) consumes the components and
    produces bundle stock."""

    bundle = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bundle_components")
    component = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="used_in_bundles")
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("1"))

    class Meta:
        unique_together = ("company", "bundle", "component")
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} × {self.component.sku} in {self.bundle.sku}"
