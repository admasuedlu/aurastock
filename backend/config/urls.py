from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.token import TenantAwareTokenObtainPairView

urlpatterns = [
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
    path("admin/", admin.site.urls),
    path("api/v1/auth/token/", TenantAwareTokenObtainPairView.as_view(), name="token_obtain_pair"),
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
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.insights.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.platform.urls")),
    path("api/v1/", include("apps.portal.urls")),
]
