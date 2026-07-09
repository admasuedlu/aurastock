from django.contrib import admin

from .models import Customer, CustomerGroup


@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "default_discount_percent"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "phone", "email", "credit_limit", "is_active"]
    search_fields = ["name", "phone", "email"]
