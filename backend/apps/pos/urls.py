from rest_framework.routers import DefaultRouter

from .views import POSSessionViewSet, POSTransactionViewSet

router = DefaultRouter()
router.register("pos-sessions", POSSessionViewSet, basename="pos-session")
router.register("pos-transactions", POSTransactionViewSet, basename="pos-transaction")

urlpatterns = router.urls
