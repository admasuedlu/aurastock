from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import BranchViewSet, CompanyMeView

router = DefaultRouter()
router.register("branches", BranchViewSet, basename="branch")

urlpatterns = [
    path("company/me/", CompanyMeView.as_view(), name="company-me"),
] + router.urls
