from rest_framework.routers import DefaultRouter

from .views import (
    BrandViewSet,
    CategoryViewSet,
    ProductVariantViewSet,
    ProductViewSet,
    UnitOfMeasureViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("brands", BrandViewSet, basename="brand")
router.register("units", UnitOfMeasureViewSet, basename="unit")
router.register("products", ProductViewSet, basename="product")
router.register("product-variants", ProductVariantViewSet, basename="product-variant")

urlpatterns = router.urls
