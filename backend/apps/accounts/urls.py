from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import ChangePasswordView, CompanySignupView, MeView, RoleViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")

urlpatterns = [
    path("auth/signup/", CompanySignupView.as_view(), name="company-signup"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
] + router.urls
