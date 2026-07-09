from django.contrib import admin

from .models import Branch, Company, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "price_monthly_etb", "max_users", "max_branches", "is_active"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "subscription_status", "default_currency", "is_active"]
    search_fields = ["name", "slug", "tin_number"]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "code", "is_main", "is_active"]
    list_filter = ["company"]
