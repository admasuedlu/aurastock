from django.contrib import admin

from .models import PortalAccount


@admin.register(PortalAccount)
class PortalAccountAdmin(admin.ModelAdmin):
    list_display = ["email", "account_type", "display_name", "company", "is_active", "last_login_at"]
    list_filter = ["is_active"]
    search_fields = ["email"]
