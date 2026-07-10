from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/", include("apps.tenants.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.products.urls")),
    path("api/v1/", include("apps.inventory.urls")),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.suppliers.urls")),
    path("api/v1/", include("apps.sales.urls")),
    path("api/v1/", include("apps.purchasing.urls")),
    path("api/v1/", include("apps.pos.urls")),
    path("api/v1/", include("apps.accounting.urls")),
]
