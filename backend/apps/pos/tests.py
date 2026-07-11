from decimal import Decimal

from apps.core.test_utils import TenantAPITestCase
from apps.inventory.models import StockItem
from apps.pos.models import POSSession, POSTransaction


class PosFlowTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.warehouse = self.make_warehouse()
        self.product = self.make_product(selling_price="100")
        self.receive_stock(self.product, self.warehouse, 10, unit_cost="60")

    def _open_session(self, opening_cash=100):
        return self.client.post("/api/v1/pos-sessions/",
                               {"warehouse": str(self.warehouse.id), "opening_cash": opening_cash},
                               format="json").data

    def _sale(self, session_id, quantity=2, tendered=500, method="cash"):
        return self.client.post("/api/v1/pos-transactions/", {
            "session": session_id, "payment_method": method, "amount_tendered": tendered,
            "items": [{"product": str(self.product.id), "quantity": quantity, "unit_price": 100}],
        }, format="json")

    def _on_hand(self):
        return StockItem.objects.get(company=self.company, warehouse=self.warehouse,
                                     product=self.product).quantity_on_hand

    def test_sale_deducts_stock_and_computes_change(self):
        session = self._open_session()
        resp = self._sale(session["id"], quantity=2, tendered=500)
        self.assertEqual(resp.status_code, 201)
        # 2 * 100 = 200 + 15% VAT = 230; change from 500 = 270.
        self.assertEqual(resp.data["total"], "230.00")
        self.assertEqual(resp.data["change_due"], "270.00")
        self.assertEqual(resp.data["status"], POSTransaction.Status.COMPLETED)
        self.assertEqual(self._on_hand(), Decimal("8.000"))

    def test_refund_restores_stock_without_diluting_cost(self):
        session = self._open_session()
        sale = self._sale(session["id"], quantity=2).data
        self.client.post(f"/api/v1/pos-transactions/{sale['id']}/refund/", {}, format="json")
        item = StockItem.objects.get(company=self.company, warehouse=self.warehouse, product=self.product)
        self.assertEqual(item.quantity_on_hand, Decimal("10.000"))     # stock back
        self.assertEqual(item.average_cost, Decimal("60.0000"))        # cost basis unchanged
        self.assertEqual(POSTransaction.objects.get(id=sale["id"]).status, POSTransaction.Status.REFUNDED)

    def test_refunding_twice_is_blocked(self):
        session = self._open_session()
        sale = self._sale(session["id"]).data
        self.client.post(f"/api/v1/pos-transactions/{sale['id']}/refund/", {}, format="json")
        again = self.client.post(f"/api/v1/pos-transactions/{sale['id']}/refund/", {}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_close_session_computes_expected_cash_and_variance(self):
        session = self._open_session(opening_cash=100)
        self._sale(session["id"], quantity=2, tendered=230, method="cash")  # cash sale of 230
        # Cashier counts 340 (100 float + 230 sale + 10 over).
        resp = self.client.post(f"/api/v1/pos-sessions/{session['id']}/close/",
                               {"closing_cash": 340}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["expected_cash"], "330.00")   # 100 + 230
        self.assertEqual(resp.data["cash_variance"], "10.00")    # 340 - 330
        self.assertEqual(resp.data["status"], POSSession.Status.CLOSED)

    def test_only_one_open_session_per_cashier(self):
        self._open_session()
        second = self.client.post("/api/v1/pos-sessions/",
                                  {"warehouse": str(self.warehouse.id), "opening_cash": 0}, format="json")
        self.assertEqual(second.status_code, 400)

    def test_sale_on_closed_session_is_rejected(self):
        session = self._open_session()
        self.client.post(f"/api/v1/pos-sessions/{session['id']}/close/", {"closing_cash": 100}, format="json")
        self.assertEqual(self._sale(session["id"]).status_code, 400)

    def test_bank_sale_does_not_count_toward_expected_cash(self):
        session = self._open_session(opening_cash=100)
        self._sale(session["id"], quantity=1, tendered=115, method="bank_transfer")
        resp = self.client.post(f"/api/v1/pos-sessions/{session['id']}/close/",
                               {"closing_cash": 100}, format="json")
        # Only cash sales bump expected cash -> still just the opening float.
        self.assertEqual(resp.data["expected_cash"], "100.00")
        self.assertEqual(resp.data["cash_variance"], "0.00")
