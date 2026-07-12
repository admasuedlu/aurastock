from rest_framework import serializers

from apps.sales.models import Invoice

from .models import PaymentIntent
from .providers import PROVIDERS


class PaymentIntentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.number", read_only=True)

    class Meta:
        model = PaymentIntent
        fields = [
            "id", "invoice", "invoice_number", "provider", "method", "amount", "status",
            "reference", "external_reference", "checkout_url", "created_at",
        ]
        read_only_fields = [
            "provider", "status", "reference", "external_reference", "checkout_url",
        ]


class CreatePaymentIntentSerializer(serializers.Serializer):
    invoice = serializers.PrimaryKeyRelatedField(queryset=Invoice.objects.none())
    method = serializers.ChoiceField(choices=[c[0] for c in PaymentIntent.method.field.choices],
                                     default="telebirr")
    provider = serializers.ChoiceField(choices=sorted(PROVIDERS), default="sandbox")
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = self.context["request"].user.company
        self.fields["invoice"].queryset = Invoice.objects.filter(company=company)
