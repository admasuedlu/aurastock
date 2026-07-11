from rest_framework.routers import DefaultRouter

from .views import GoodsReceiptViewSet, PurchaseOrderViewSet, PurchaseRequestViewSet

router = DefaultRouter()
router.register("purchase-requests", PurchaseRequestViewSet, basename="purchase-request")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("goods-receipts", GoodsReceiptViewSet, basename="goods-receipt")

urlpatterns = router.urls
