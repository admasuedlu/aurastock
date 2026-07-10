from rest_framework import serializers

from apps.tenants.models import Company, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    company_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id", "name", "code", "price_monthly_etb", "max_users", "max_branches",
            "max_warehouses", "features", "is_active", "company_count", "created_at",
        ]


class TenantCompanySerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="subscription_plan.name", read_only=True, default=None)
    plan_code = serializers.CharField(source="subscription_plan.code", read_only=True, default=None)
    user_count = serializers.IntegerField(read_only=True)
    branch_count = serializers.IntegerField(read_only=True)
    warehouse_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Company
        fields = [
            "id", "name", "slug", "email", "phone", "city", "tin_number",
            "subscription_plan", "plan_name", "plan_code", "subscription_status",
            "trial_ends_at", "is_active", "user_count", "branch_count",
            "warehouse_count", "created_at",
        ]
        read_only_fields = ["id", "name", "slug", "created_at"]
