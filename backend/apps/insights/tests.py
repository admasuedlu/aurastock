from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.core.test_utils import TenantAPITestCase
from apps.inventory.models import StockMovement
from apps.inventory.services import stock_out


class ReorderSuggestionTests(TenantAPITestCase):
    def test_suggests_quantity_from_actual_sales_velocity(self):
        warehouse = self.make_warehouse()
        product = self.make_product(reorder_level=Decimal("100"), safety_stock=Decimal("0"))
        self.receive_stock(product, warehouse, 35, unit_cost="10")
        stock_out(company=self.company, warehouse=warehouse, product=product,
                  quantity=Decimal("30"), user=self.user)  # sold 30 in the window; 5 left, below reorder 100

        rows = self.client.get("/api/v1/insights/reorder-suggestions/").data["rows"]
        row = next(r for r in rows if r["product_sku"] == product.sku)
        # avg daily 30/30 = 1 -> 1*7 lead + 0 safety - 5 available = 2
        self.assertEqual(float(row["suggested_quantity"]), 2.0)

    def test_well_stocked_product_is_not_suggested(self):
        warehouse = self.make_warehouse()
        product = self.make_product(sku="PLENTY-1", reorder_level=Decimal("1"))
        self.receive_stock(product, warehouse, 100, unit_cost="1")  # far above reorder
        rows = self.client.get("/api/v1/insights/reorder-suggestions/").data["rows"]
        self.assertFalse(any(r["product_sku"] == "PLENTY-1" for r in rows))


class InsightsHistoryTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.warehouse = self.make_warehouse()

    def _movement(self, product, quantity, days_ago, reference="X"):
        movement = StockMovement.objects.create(
            company=self.company, warehouse=self.warehouse, product=product,
            movement_type=StockMovement.MovementType.STOCK_OUT,
            quantity=Decimal(str(quantity)), reference=reference,
        )
        StockMovement.objects.filter(id=movement.id).update(
            created_at=timezone.now() - timedelta(days=days_ago))
        return movement

    def test_demand_forecast_detects_increasing_trend(self):
        product = self.make_product(sku="TREND-1")
        # First half of the 60-day window sells 1/day, second half sells 10/day.
        for days_ago in range(46, 60):   # older
            self._movement(product, 1, days_ago)
        for days_ago in range(0, 14):    # recent
            self._movement(product, 10, days_ago)

        data = self.client.get("/api/v1/insights/demand-forecast/", {"product": str(product.id)}).data
        self.assertEqual(data["trend"], "increasing")
        forecast = data["forecast"]
        self.assertTrue(forecast)
        # OLS slope is positive -> the projection rises across the horizon.
        self.assertGreaterEqual(forecast[-1]["quantity"], forecast[0]["quantity"])

    def test_anomaly_detection_flags_the_outlier_only(self):
        product = self.make_product(sku="ANOM-1")
        # A steady ~5-unit baseline (>= 5 points) plus one planted 60-unit spike today.
        for days_ago in (70, 60, 50, 40, 30, 20, 10):
            self._movement(product, 5, days_ago)
        self._movement(product, 60, 0, reference="INV-SPIKE")

        rows = self.client.get("/api/v1/insights/anomalies/", {"days": 7}).data["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0]["quantity"]), 60.0)
        self.assertEqual(rows[0]["reference"], "INV-SPIKE")

    def test_no_anomaly_without_enough_history(self):
        product = self.make_product(sku="THIN-1")
        # Only 2 points -> below the minimum for a meaningful stdev; nothing flagged.
        self._movement(product, 5, 10)
        self._movement(product, 60, 0)
        rows = self.client.get("/api/v1/insights/anomalies/", {"days": 7}).data["rows"]
        self.assertEqual(rows, [])
