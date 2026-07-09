from django.contrib import admin

from .models import Invoice, InvoiceItem, Quotation, QuotationItem, SalesOrder, SalesOrderItem, SalesPayment


class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 0


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ["number", "customer", "company", "status", "total"]
    list_filter = ["company", "status"]
    inlines = [QuotationItemInline]


class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 0


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ["number", "customer", "company", "status", "total"]
    list_filter = ["company", "status"]
    inlines = [SalesOrderItemInline]


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class SalesPaymentInline(admin.TabularInline):
    model = SalesPayment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["number", "customer", "company", "status", "total", "amount_paid"]
    list_filter = ["company", "status"]
    inlines = [InvoiceItemInline, SalesPaymentInline]
