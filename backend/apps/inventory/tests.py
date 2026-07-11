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


class SerialTrackingTests(TenantAPITestCase):
    def _serialized(self):
        return self.make_product(sku="PHONE-1", track_serial=True)

    def test_receive_requires_matching_serial_count(self):
        wh = self.make_warehouse()
        p = self._serialized()
        with self.assertRaises(ValidationError):  # 2 serials for qty 3
            self.receive_stock(p, wh, 3, unit_cost="100", serial_numbers=["A", "B"])

    def test_quantity_must_be_whole(self):
        wh = self.make_warehouse()
        p = self._serialized()
        with self.assertRaises(ValidationError):
            self.receive_stock(p, wh, "2.5", unit_cost="100", serial_numbers=["A", "B"])

    def test_duplicate_and_clashing_serials_rejected(self):
        from apps.inventory.models import SerialUnit
        wh = self.make_warehouse()
        p = self._serialized()
        with self.assertRaises(ValidationError):  # dupes within the request
            self.receive_stock(p, wh, 2, unit_cost="100", serial_numbers=["A", "A"])
        self.receive_stock(p, wh, 1, unit_cost="100", serial_numbers=["SN-1"])
        with self.assertRaises(ValidationError):  # SN-1 already on record
            self.receive_stock(p, wh, 1, unit_cost="100", serial_numbers=["SN-1"])
        self.assertEqual(SerialUnit.objects.filter(product=p).count(), 1)

    def test_receive_creates_in_stock_units(self):
        from apps.inventory.models import SerialUnit
        wh = self.make_warehouse()
        p = self._serialized()
        self.receive_stock(p, wh, 3, unit_cost="100", serial_numbers=["S1", "S2", "S3"])
        self.assertEqual(SerialUnit.objects.filter(
            product=p, warehouse=wh, status=SerialUnit.Status.IN_STOCK).count(), 3)
        self.assertEqual(StockItem.objects.get(company=self.company, warehouse=wh, product=p).quantity_on_hand,
                         Decimal("3.000"))

    def test_sale_auto_selects_and_marks_out(self):
        from apps.inventory.models import SerialUnit
        wh = self.make_warehouse()
        p = self._serialized()
        self.receive_stock(p, wh, 3, unit_cost="100", serial_numbers=["S1", "S2", "S3"])
        # Sales path passes no serial info -> auto FIFO pick of 2.
        stock_out(company=self.company, warehouse=wh, product=p, quantity=Decimal("2"),
                  reference="INV-001", user=self.user)
        self.assertEqual(SerialUnit.objects.filter(product=p, status=SerialUnit.Status.IN_STOCK).count(), 1)
        out_units = SerialUnit.objects.filter(product=p, status=SerialUnit.Status.OUT)
        self.assertEqual(out_units.count(), 2)
        self.assertTrue(all(u.warehouse_id is None and u.reference == "INV-001" for u in out_units))

    def test_explicit_serial_stock_out(self):
        from apps.inventory.models import SerialUnit
        wh = self.make_warehouse()
        p = self._serialized()
        self.receive_stock(p, wh, 3, unit_cost="100", serial_numbers=["S1", "S2", "S3"])
        stock_out(company=self.company, warehouse=wh, product=p, quantity=Decimal("1"),
                  serial_numbers=["S2"], reference="INV-9", user=self.user)
        self.assertEqual(SerialUnit.objects.get(product=p, serial_number="S2").status, SerialUnit.Status.OUT)
        self.assertEqual(SerialUnit.objects.filter(
            product=p, serial_number__in=["S1", "S3"], status=SerialUnit.Status.IN_STOCK).count(), 2)

    def test_transfer_moves_serial_to_destination_warehouse(self):
        from apps.inventory.models import SerialUnit
        src = self.make_warehouse(code="WH1")
        dst = self.make_warehouse(code="WH2", name="Second")
        p = self._serialized()
        self.receive_stock(p, src, 2, unit_cost="100", serial_numbers=["S1", "S2"])
        transfer_stock(company=self.company, from_warehouse=src, to_warehouse=dst,
                       product=p, quantity=Decimal("1"), serial_numbers=["S1"], user=self.user)
        moved = SerialUnit.objects.get(product=p, serial_number="S1")
        self.assertEqual(moved.warehouse_id, dst.id)
        self.assertEqual(moved.status, SerialUnit.Status.IN_STOCK)

    def test_insufficient_serials_blocks_stock_out(self):
        wh = self.make_warehouse()
        p = self._serialized()
        self.receive_stock(p, wh, 1, unit_cost="100", serial_numbers=["S1"])
        with self.assertRaises(ValidationError):
            stock_out(company=self.company, warehouse=wh, product=p, quantity=Decimal("2"), user=self.user)

    def test_serial_units_api_supports_warranty_lookup(self):
        wh = self.make_warehouse()
        p = self._serialized()
        self.receive_stock(p, wh, 2, unit_cost="100", serial_numbers=["S1", "S2"])
        stock_out(company=self.company, warehouse=wh, product=p, quantity=Decimal("1"),
                  serial_numbers=["S1"], reference="INV-77", user=self.user)
        resp = self.client.get("/api/v1/serial-units/", {"serial_number": "S1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        row = resp.data["results"][0]
        self.assertEqual(row["status"], "out")
        self.assertEqual(row["reference"], "INV-77")
