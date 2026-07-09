from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel, TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.SlugField(unique=True)
    price_monthly_etb = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    max_users = models.PositiveIntegerField(default=5)
    max_branches = models.PositiveIntegerField(default=1)
    max_warehouses = models.PositiveIntegerField(default=1)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price_monthly_etb"]

    def __str__(self):
        return self.name


class Company(TimeStampedModel):
    """The tenant. All tenant-scoped data hangs off this via `company` FKs."""

    class SubscriptionStatus(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(unique=True)
    tin_number = models.CharField("TIN", max_length=50, blank=True)
    vat_registered = models.BooleanField(default=False)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)

    default_currency = models.CharField(max_length=3, default="ETB")
    timezone = models.CharField(max_length=64, default="Africa/Addis_Ababa")
    use_ethiopian_calendar = models.BooleanField(default=True)

    subscription_plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name="companies", null=True
    )
    subscription_status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING
    )
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class Branch(CompanyScopedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_main = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["-is_main", "name"]

    def __str__(self):
        return f"{self.name} ({self.company.name})"
