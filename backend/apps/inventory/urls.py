from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import (
    BatchViewSet,
    StockAdjustmentView,
    StockInView,
    StockItemViewSet,
    StockMovementViewSet,
    StockOutView,
    StockTransferView,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("stock-items", StockItemViewSet, basename="stock-item")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("batches", BatchViewSet, basename="batch")

urlpatterns = [
    path("inventory/stock-in/", StockInView.as_view(), name="stock-in"),
    path("inventory/stock-out/", StockOutView.as_view(), name="stock-out"),
    path("inventory/stock-transfer/", StockTransferView.as_view(), name="stock-transfer"),
    path("inventory/stock-adjustment/", StockAdjustmentView.as_view(), name="stock-adjustment"),
] + router.urls
