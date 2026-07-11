from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.core.viewsets import CompanyScopedViewSet

from .models import Brand, BundleComponent, Category, Product, ProductVariant, UnitOfMeasure
from .serializers import (
    BrandSerializer,
    BundleComponentSerializer,
    CategorySerializer,
    ProductSerializer,
    ProductVariantSerializer,
    UnitOfMeasureSerializer,
)


class CategoryViewSet(CompanyScopedViewSet):
    queryset = Category.objects.select_related("parent").all()
    serializer_class = CategorySerializer
    permission_module = "products"
    filterset_fields = ["parent", "is_active"]
    search_fields = ["name"]


class BrandViewSet(CompanyScopedViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_module = "products"
    filterset_fields = ["is_active"]
    search_fields = ["name"]


class UnitOfMeasureViewSet(CompanyScopedViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer
    permission_module = "products"
    search_fields = ["name", "symbol"]


class ProductViewSet(CompanyScopedViewSet):
    queryset = Product.objects.select_related("category", "brand", "unit").prefetch_related("variants").all()
    serializer_class = ProductSerializer
    permission_module = "products"
    filterset_fields = ["category", "brand", "product_type", "is_active"]
    search_fields = ["name", "sku", "barcode"]
    ordering_fields = ["name", "created_at", "selling_price"]

    @action(detail=False, methods=["get"])
    def lookup(self, request):
        """Resolve a scanned barcode to a single product. Exact match on the
        product's own barcode, falling back to a variant barcode (returning the
        parent product plus which variant matched). This is the scanner's
        scan->product step, distinct from the fuzzy `?search=` filter."""
        code = request.query_params.get("barcode", "").strip()
        if not code:
            raise DRFValidationError({"barcode": "A barcode is required."})

        product = self.get_queryset().filter(barcode=code).first()
        variant_id = None
        if product is None:
            variant = (
                ProductVariant.objects
                .filter(company_id=request.user.company_id, barcode=code)
                .select_related("product").first()
            )
            if variant is not None:
                product, variant_id = variant.product, variant.id

        if product is None:
            return Response({"detail": "No product found for that barcode."}, status=404)
        return Response({
            "product": ProductSerializer(product).data,
            "variant_id": str(variant_id) if variant_id else None,
        })


class ProductVariantViewSet(CompanyScopedViewSet):
    queryset = ProductVariant.objects.select_related("product").all()
    serializer_class = ProductVariantSerializer
    permission_module = "products"
    filterset_fields = ["product", "is_active"]
    search_fields = ["sku", "barcode"]


class BundleComponentViewSet(CompanyScopedViewSet):
    """Manage a bundle's bill of materials -- the component lines the assemble
    operation consumes. Filter by `?bundle=<id>` to load one bundle's recipe."""

    queryset = BundleComponent.objects.select_related("component", "bundle").all()
    serializer_class = BundleComponentSerializer
    permission_module = "products"
    filterset_fields = ["bundle", "component"]
