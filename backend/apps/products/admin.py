from django.contrib import admin

from .models import Brand, Category, Product, ProductVariant, UnitOfMeasure


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "parent", "is_active"]
    list_filter = ["company", "is_active"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "is_active"]


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ["name", "symbol", "company", "base_unit", "conversion_factor"]


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "company", "category", "selling_price", "is_active"]
    list_filter = ["company", "category", "product_type", "is_active"]
    search_fields = ["name", "sku", "barcode"]
    inlines = [ProductVariantInline]
