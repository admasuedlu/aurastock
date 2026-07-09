from rest_framework import serializers

from apps.core.numbering import next_value

from .models import Brand, Category, Product, ProductVariant, UnitOfMeasure


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent", "image", "is_active"]
        read_only_fields = ["company"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "logo", "is_active"]


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = ["id", "name", "symbol", "base_unit", "conversion_factor"]


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            "id", "product", "sku", "barcode", "attributes",
            "cost_price", "selling_price", "image", "is_active",
        ]
        read_only_fields = ["sku"]

    def create(self, validated_data):
        product = validated_data["product"]
        validated_data["sku"] = next_value(
            validated_data["company"], "variant_sku", default_prefix=f"{product.sku}-"
        )
        return super().create(validated_data)


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    unit_symbol = serializers.CharField(source="unit.symbol", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "barcode", "description",
            "category", "category_name", "brand", "brand_name",
            "unit", "unit_symbol", "product_type",
            "cost_price", "selling_price", "tax_rate_percent",
            "reorder_level", "safety_stock",
            "track_serial", "track_batch", "track_expiry",
            "image", "is_active", "variants", "created_at",
        ]
        read_only_fields = ["sku"]

    def create(self, validated_data):
        validated_data["sku"] = next_value(validated_data["company"], "product_sku", default_prefix="PRD-")
        return super().create(validated_data)
