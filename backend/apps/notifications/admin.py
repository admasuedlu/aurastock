from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "notification_type", "company", "recipient", "is_read", "created_at"]
    list_filter = ["company", "notification_type", "is_read"]
    search_fields = ["title", "message", "reference"]
