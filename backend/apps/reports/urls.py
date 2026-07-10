from django.urls import path

from .views import DeadStockView, InventoryValuationView, SalesSummaryView, TopProductsView

urlpatterns = [
    path("reports/sales-summary/", SalesSummaryView.as_view(), name="sales-summary"),
    path("reports/top-products/", TopProductsView.as_view(), name="top-products"),
    path("reports/inventory-valuation/", InventoryValuationView.as_view(), name="inventory-valuation"),
    path("reports/dead-stock/", DeadStockView.as_view(), name="dead-stock"),
]
