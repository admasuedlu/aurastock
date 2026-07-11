from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.core.test_utils import TenantAPITestCase
from apps.inventory.models import BatchStock, StockItem
from apps.inventory.services import stock_in, stock_out, transfer_stock


class WeightedAverageCostingTests(TenantAPITestCase):
    def test_weighted_average_cost_blends_receipts(self):
        wh = self.make_warehouse()
        p = self.make_product()
        self.receive_stock(p, wh, 10, unit_cost="5")   # value 50
        self.receive_stock(p, wh, 10, unit_cost="7")   # value 70 -> avg (120/20)=6
        item = StockItem.objects.get(company=self.company, warehouse=wh, product=p)
        self.assertEqual(item.quantity_on_hand, Decimal("20.000"))
        self.assertEqual(item.average_cost, Decimal("6.0000"))

    def test_stock_out_records_average_cost_and_does_not_change_it(self):
        wh = self.make_warehouse()
        p = self.make_product()
        self.receive_stock(p, wh, 10, unit_cost="6")
        movement = stock_out(company=self.company, warehouse=wh, product=p,
                             quantity=Decimal("4"), user=self.user)
        self.assertEqual(movement.unit_cost, Decimal("6.0000"))
        item = StockItem.objects.get(company=self.company, warehouse=wh, product=p)
        self.assertEqual(item.quantity_on_hand, Decimal("6.000"))
        self.assertEqual(item.average_cost, Decimal("6.0000"))

    def test_insufficient_stock_is_blocked(self):
        wh = self.make_warehouse()
        p = self.make_product()
        self.receive_stock(p, wh, 3, unit_cost="6")
        with self.assertRaises(ValidationError):
            stock_out(company=self.company, warehouse=wh, product=p,
                      quantity=Decimal("5"), user=self.user)


class BatchTrackingTests(TenantAPITestCase):
    def _tracked(self):
        return self.make_product(sku="VAC-1", track_batch=True, track_expiry=True)

    def test_batch_number_required_for_tracked_product(self):
        wh = self.make_warehouse()
        p = self._tracked()
        with self.assertRaises(ValidationError):
            stock_in(company=self.company, warehouse=wh, product=p,
                     quantity=Decimal("5"), unit_cost=Decimal("5"), user=self.user)

    def test_expiry_required_when_tracking_expiry(self):
        wh = self.make_warehouse()
        p = self._tracked()
        with self.assertRaises(ValidationError):
            stock_in(company=self.company, warehouse=wh, product=p, quantity=Decimal("5"),
                     unit_cost=Decimal("5"), user=self.user, batch_number="B1")

    def test_fefo_consumes_earliest_expiry_first(self):
        wh = self.make_warehouse()
        p = self._tracked()
        self.receive_stock(p, wh, 10, unit_cost="5", batch_number="B-LATER",
                           expiry_date=date(2026, 12, 1))
        self.receive_stock(p, wh, 5, unit_cost="6", batch_number="B-SOONER",
                           expiry_date=date(2026, 8, 1))
        stock_out(company=self.company, warehouse=wh, product=p, quantity=Decimal("7"), user=self.user)

        sooner = BatchStock.objects.get(warehouse=wh, product=p, batch__batch_number="B-SOONER")
        later = BatchStock.objects.get(warehouse=wh, product=p, batch__batch_number="B-LATER")
        self.assertEqual(sooner.quantity_on_hand, Decimal("0.000"))   # fully drained first
        self.assertEqual(later.quantity_on_hand, Decimal("8.000"))    # then 2 taken from it

    def test_transfer_carries_batch_to_destination(self):
        src = self.make_warehouse(code="WH1")
        dst = self.make_warehouse(code="WH2", name="Second")
        p = self._tracked()
        self.receive_stock(p, src, 10, unit_cost="5", batch_number="B1", expiry_date=date(2026, 12, 1))
        transfer_stock(company=self.company, from_warehouse=src, to_warehouse=dst,
                       product=p, quantity=Decimal("3"), user=self.user)
        dst_stock = BatchStock.objects.get(warehouse=dst, product=p, batch__batch_number="B1")
        self.assertEqual(dst_stock.quantity_on_hand, Decimal("3.000"))

    def test_untracked_product_creates_no_batches(self):
        wh = self.make_warehouse()
        p = self.make_product(sku="PLAIN-1")  # no tracking flags
        self.receive_stock(p, wh, 50, unit_cost="2")
        stock_out(company=self.company, warehouse=wh, product=p, quantity=Decimal("20"), user=self.user)
        item = StockItem.objects.get(company=self.company, warehouse=wh, product=p)
        self.assertEqual(item.quantity_on_hand, Decimal("30.000"))
        self.assertEqual(BatchStock.objects.filter(product=p).count(), 0)


class BatchAPITests(TenantAPITestCase):
    def test_expiring_report_lists_only_in_stock_batches(self):
        wh = self.make_warehouse()
        p = self.make_product(sku="VAC-1", track_batch=True, track_expiry=True)
        soon = date.today() + timedelta(days=10)
        self.receive_stock(p, wh, 5, unit_cost="5", batch_number="B1", expiry_date=soon)
        # Drain it -> should drop out of the expiring report (quantity 0)
        self.receive_stock(p, wh, 3, unit_cost="5", batch_number="B2", expiry_date=soon)
        stock_out(company=self.company, warehouse=wh, product=p, quantity=Decimal("5"), user=self.user)

        resp = self.client.get("/api/v1/batches/expiring/", {"days": 30})
        self.assertEqual(resp.status_code, 200)
        numbers = {row["batch_number"] for row in resp.data["results"]}
        # B1 (5) fully consumed first via FEFO (same expiry, created first); B2 has 3 left
        self.assertEqual(numbers, {"B2"})
