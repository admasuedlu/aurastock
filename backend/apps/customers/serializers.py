from rest_framework import serializers

from .models import Customer, CustomerGroup


class CustomerGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerGroup
        fields = ["id", "name", "default_discount_percent"]


class CustomerSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id", "name", "group", "group_name", "phone", "email", "tin_number",
            "address", "city", "credit_limit", "is_active", "created_at",
        ]
