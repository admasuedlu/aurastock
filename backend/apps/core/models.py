import uuid

from django.db import models


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CompanyScopedManager(models.Manager):
    """Default manager for tenant-scoped models. Views must still explicitly
    filter by the requesting user's company; this manager just guarantees
    every tenant-scoped model exposes a `company` field consistently."""


class CompanyScopedModel(TimeStampedModel):
    company = models.ForeignKey(
        "tenants.Company",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
    )

    objects = CompanyScopedManager()

    class Meta:
        abstract = True
