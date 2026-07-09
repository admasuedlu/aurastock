from django.contrib import admin

from .models import POSSession, POSTransaction, POSTransactionItem


@admin.register(POSSession)
class POSSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "company", "cashier", "warehouse", "status", "opening_cash", "cash_variance"]
    list_filter = ["company", "status"]


class POSTransactionItemInline(admin.TabularInline):
    model = POSTransactionItem
    extra = 0


@admin.register(POSTransaction)
class POSTransactionAdmin(admin.ModelAdmin):
    list_display = ["number", "company", "session", "customer", "total", "payment_method", "status"]
    list_filter = ["company", "status", "payment_method"]
    inlines = [POSTransactionItemInline]
