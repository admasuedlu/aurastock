from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import CompanyScopedModel


class PortalAccount(CompanyScopedModel):
    """Login for an external customer or supplier contact. Deliberately not a
    User: every staff viewset trusts a User's company FK for row visibility,
    and a customer modeled that way would see the entire tenant's data.
    Portal users authenticate with their own signed, expiring token instead
    of a JWT, so staff endpoints reject them by construction."""

    customer = models.OneToOneField(
        "customers.Customer", on_delete=models.CASCADE, related_name="portal_account", null=True, blank=True,
    )
    supplier = models.OneToOneField(
        "suppliers.Supplier", on_delete=models.CASCADE, related_name="portal_account", null=True, blank=True,
    )
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(customer__isnull=False, supplier__isnull=True)
                    | models.Q(customer__isnull=True, supplier__isnull=False)
                ),
                name="portal_account_exactly_one_of_customer_or_supplier",
            )
        ]

    def __str__(self):
        return self.email

    def clean(self):
        if bool(self.customer_id) == bool(self.supplier_id):
            raise ValidationError("A portal account must link to exactly one customer or supplier.")

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def is_authenticated(self):
        """Mirrors django.contrib.auth's User/AnonymousUser contract so
        DRF's IsAuthenticated permission works unchanged for this non-User
        principal."""
        return True

    @property
    def account_type(self):
        return "customer" if self.customer_id else "supplier"

    @property
    def display_name(self):
        return self.customer.name if self.customer_id else self.supplier.name
