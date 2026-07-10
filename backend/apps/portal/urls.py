from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    PortalInvoiceViewSet,
    PortalLoginView,
    PortalPurchaseOrderViewSet,
    PortalQuotationViewSet,
    PortalSalesOrderViewSet,
)

router = DefaultRouter()
router.register("portal/quotations", PortalQuotationViewSet, basename="portal-quotation")
router.register("portal/sales-orders", PortalSalesOrderViewSet, basename="portal-sales-order")
router.register("portal/invoices", PortalInvoiceViewSet, basename="portal-invoice")
router.register("portal/purchase-orders", PortalPurchaseOrderViewSet, basename="portal-purchase-order")

urlpatterns = [
    path("portal/login/", PortalLoginView.as_view(), name="portal-login"),
    *router.urls,
]
