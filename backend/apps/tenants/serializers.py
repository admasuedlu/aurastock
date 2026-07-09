from rest_framework import serializers

from .models import Branch, Company, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id", "name", "code", "price_monthly_etb",
            "max_users", "max_branches", "max_warehouses", "features", "is_active",
        ]


class CompanySerializer(serializers.ModelSerializer):
    subscription_plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = Company
        fields = [
            "id", "name", "legal_name", "slug", "tin_number", "vat_registered",
            "phone", "email", "address", "city", "logo",
            "default_currency", "timezone", "use_ethiopian_calendar",
            "subscription_plan", "subscription_status", "trial_ends_at", "is_active",
            "created_at",
        ]
        read_only_fields = ["subscription_status", "trial_ends_at"]


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id", "company", "name", "code", "address", "city", "phone",
            "is_main", "is_active", "created_at",
        ]
        read_only_fields = ["company"]
