from apps.core.viewsets import CompanyScopedViewSet

from .models import Brand, Category, Product, ProductVariant, UnitOfMeasure
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductSerializer,
    ProductVariantSerializer,
    UnitOfMeasureSerializer,
)


class CategoryViewSet(CompanyScopedViewSet):
    queryset = Category.objects.select_related("parent").all()
    serializer_class = CategorySerializer
    filterset_fields = ["parent", "is_active"]
    search_fields = ["name"]


class BrandViewSet(CompanyScopedViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name"]


class UnitOfMeasureViewSet(CompanyScopedViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer
    search_fields = ["name", "symbol"]


class ProductViewSet(CompanyScopedViewSet):
    queryset = Product.objects.select_related("category", "brand", "unit").prefetch_related("variants").all()
    serializer_class = ProductSerializer
    filterset_fields = ["category", "brand", "product_type", "is_active"]
    search_fields = ["name", "sku", "barcode"]
    ordering_fields = ["name", "created_at", "selling_price"]


class ProductVariantViewSet(CompanyScopedViewSet):
    queryset = ProductVariant.objects.select_related("product").all()
    serializer_class = ProductVariantSerializer
    filterset_fields = ["product", "is_active"]
    search_fields = ["sku", "barcode"]
