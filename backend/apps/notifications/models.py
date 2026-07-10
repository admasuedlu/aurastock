from django.db import models

from apps.core.models import CompanyScopedModel


class Notification(CompanyScopedModel):
    class NotificationType(models.TextChoices):
        LOW_STOCK = "low_stock", "Low stock"
        OVERDUE_INVOICE = "overdue_invoice", "Overdue invoice"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notifications", null=True, blank=True,
        help_text="Null means every user in the company can see it (e.g. low-stock alerts).",
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    reference = models.CharField(max_length=100, blank=True, help_text="Related record, e.g. an invoice number")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "recipient", "is_read"])]

    def __str__(self):
        return self.title
