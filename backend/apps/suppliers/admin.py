from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "phone", "email", "payment_terms_days", "is_active"]
    search_fields = ["name", "phone", "email"]
