from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel


class CustomerGroup(CompanyScopedModel):
    name = models.CharField(max_length=100)
    default_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = ("company", "name")

    def __str__(self):
        return self.name


class Customer(CompanyScopedModel):
    name = models.CharField(max_length=255)
    group = models.ForeignKey(CustomerGroup, on_delete=models.SET_NULL, related_name="customers", null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    tin_number = models.CharField("TIN", max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
