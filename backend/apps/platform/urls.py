from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PlatformOverviewView, SubscriptionPlanViewSet, TenantCompanyViewSet

router = DefaultRouter()
router.register("platform/plans", SubscriptionPlanViewSet, basename="platform-plan")
router.register("platform/companies", TenantCompanyViewSet, basename="platform-company")

urlpatterns = [
    path("platform/overview/", PlatformOverviewView.as_view(), name="platform-overview"),
] + router.urls
