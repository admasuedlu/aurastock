from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import CompanyScopedModel, TimeStampedModel


class Permission(TimeStampedModel):
    """A single grantable capability, e.g. `products.create`,
    `purchase_orders.approve`. Global catalog shared by all tenants;
    seeded via `manage.py seed_permissions`."""

    code = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["module", "code"]

    def __str__(self):
        return self.code


class Role(CompanyScopedModel):
    """Company-scoped role. Companies get a starter set of roles (Owner,
    Admin, Inventory Manager, ...) seeded on signup and can add custom ones."""

    name = models.CharField(max_length=100)
    is_system = models.BooleanField(default=False, help_text="Seeded default role; cannot be deleted")
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    class Meta:
        unique_together = ("company", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} @ {self.company.name}"


class User(AbstractUser):
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    email = models.EmailField(unique=True)
    company = models.ForeignKey(
        "tenants.Company", on_delete=models.CASCADE, related_name="users", null=True, blank=True,
        help_text="Null for platform-level staff (SaaS admins)",
    )
    branch = models.ForeignKey(
        "tenants.Branch", on_delete=models.SET_NULL, related_name="users", null=True, blank=True,
    )
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, related_name="users", null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_company_owner = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=5, default="en")
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username
