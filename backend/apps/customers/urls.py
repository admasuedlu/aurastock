from rest_framework.routers import DefaultRouter

from .views import CustomerGroupViewSet, CustomerViewSet

router = DefaultRouter()
router.register("customer-groups", CustomerGroupViewSet, basename="customer-group")
router.register("customers", CustomerViewSet, basename="customer")

urlpatterns = router.urls
