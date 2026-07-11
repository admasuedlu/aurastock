from django.contrib import admin

from .models import PaymentIntent


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ["reference", "invoice", "company", "provider", "method", "amount", "status"]
    list_filter = ["company", "provider", "status"]
    search_fields = ["reference", "external_reference", "invoice__number"]
