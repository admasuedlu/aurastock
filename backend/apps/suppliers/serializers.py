from rest_framework import serializers

from .models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id", "name", "contact_person", "phone", "email", "tin_number",
            "address", "city", "payment_terms_days", "is_active", "created_at",
        ]
