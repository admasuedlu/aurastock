from django.urls import path

from .views import (
    AbcAnalysisView,
    DeadStockView,
    InventoryValuationView,
    PurchaseSummaryView,
    SalesSummaryView,
    TopProductsView,
)

urlpatterns = [
    path("reports/sales-summary/", SalesSummaryView.as_view(), name="sales-summary"),
    path("reports/purchase-summary/", PurchaseSummaryView.as_view(), name="purchase-summary"),
    path("reports/top-products/", TopProductsView.as_view(), name="top-products"),
    path("reports/abc-analysis/", AbcAnalysisView.as_view(), name="abc-analysis"),
    path("reports/inventory-valuation/", InventoryValuationView.as_view(), name="inventory-valuation"),
    path("reports/dead-stock/", DeadStockView.as_view(), name="dead-stock"),
]
