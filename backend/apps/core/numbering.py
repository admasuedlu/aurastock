from django.db import models, transaction

from .models import CompanyScopedModel


class NumberSequence(CompanyScopedModel):
    """Per-company, per-document counters (SKU, invoice #, PO #, ...) so
    every numbered document type gets gap-free, tenant-scoped numbering."""

    key = models.CharField(max_length=50, help_text="e.g. product_sku, invoice, purchase_order")
    prefix = models.CharField(max_length=20, blank=True)
    next_number = models.PositiveIntegerField(default=1)
    padding = models.PositiveSmallIntegerField(default=5)

    class Meta:
        unique_together = ("company", "key")

    def __str__(self):
        return f"{self.company_id}:{self.key} -> {self.next_number}"


@transaction.atomic
def next_value(company, key: str, default_prefix: str = "") -> str:
    seq, _ = NumberSequence.objects.select_for_update().get_or_create(
        company=company, key=key, defaults={"prefix": default_prefix},
    )
    value = f"{seq.prefix}{seq.next_number:0{seq.padding}d}"
    seq.next_number += 1
    seq.save(update_fields=["next_number"])
    return value
