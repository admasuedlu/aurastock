from decimal import Decimal

from apps.core.test_utils import TenantAPITestCase
from apps.inventory.models import StockItem
from apps.purchasing.models import PurchaseOrder, PurchaseRequest


class PurchaseRequestWorkflowTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product(cost_price="60")
        self.supplier = self.make_supplier()

    def _make_request(self, with_supplier=False, quantity=10):
        payload = {"items": [{"product": str(self.product.id), "quantity": quantity, "unit_price": 60}]}
        if with_supplier:
            payload["supplier"] = str(self.supplier.id)
        return self.client.post("/api/v1/purchase-requests/", payload, format="json").data

    def test_happy_path_draft_to_converted(self):
        pr = self._make_request()
        self.assertEqual(pr["status"], "draft")
        pid = pr["id"]

        # Illegal transitions from draft
        self.assertEqual(self.client.post(f"/api/v1/purchase-requests/{pid}/approve/", {}, format="json").status_code, 400)
        self.assertEqual(self.client.post(f"/api/v1/purchase-requests/{pid}/convert-to-po/", {}, format="json").status_code, 400)

        self.client.post(f"/api/v1/purchase-requests/{pid}/submit/", {}, format="json")
        approved = self.client.post(f"/api/v1/purchase-requests/{pid}/approve/", {}, format="json").data
        self.assertEqual(approved["status"], "approved")
        self.assertIsNotNone(approved["approved_at"])

        # Convert (supplier supplied at convert time)
        po = self.client.post(f"/api/v1/purchase-requests/{pid}/convert-to-po/",
                              {"supplier": str(self.supplier.id)}, format="json")
        self.assertEqual(po.status_code, 201)
        self.assertEqual(str(po.data["purchase_request"]), str(pid))
        self.assertEqual(len(po.data["items"]), 1)
        self.assertEqual(PurchaseRequest.objects.get(id=pid).status, "converted")

        # Cannot convert twice
        again = self.client.post(f"/api/v1/purchase-requests/{pid}/convert-to-po/",
                                 {"supplier": str(self.supplier.id)}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_reject_captures_reason_and_blocks_conversion(self):
        pr = self._make_request()
        pid = pr["id"]
        self.client.post(f"/api/v1/purchase-requests/{pid}/submit/", {}, format="json")
        rejected = self.client.post(f"/api/v1/purchase-requests/{pid}/reject/",
                                    {"reason": "Over budget"}, format="json").data
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(rejected["rejection_reason"], "Over budget")
        convert = self.client.post(f"/api/v1/purchase-requests/{pid}/convert-to-po/",
                                   {"supplier": str(self.supplier.id)}, format="json")
        self.assertEqual(convert.status_code, 400)

    def test_convert_without_supplier_is_rejected(self):
        pr = self._make_request()  # no supplier
        pid = pr["id"]
        self.client.post(f"/api/v1/purchase-requests/{pid}/submit/", {}, format="json")
        self.client.post(f"/api/v1/purchase-requests/{pid}/approve/", {}, format="json")
        resp = self.client.post(f"/api/v1/purchase-requests/{pid}/convert-to-po/", {}, format="json")
        self.assertEqual(resp.status_code, 400)


class GoodsReceiptTests(TenantAPITestCase):
    def test_receiving_goods_adds_stock_and_updates_po(self):
        wh = self.make_warehouse()
        supplier = self.make_supplier()
        product = self.make_product(cost_price="60")
        po = self.client.post("/api/v1/purchase-orders/", {
            "supplier": str(supplier.id),
            "items": [{"product": str(product.id), "quantity": 20, "unit_price": 60}],
        }, format="json").data
        po_item_id = po["items"][0]["id"]

        # Partial receipt of 8
        self.client.post("/api/v1/goods-receipts/", {
            "purchase_order": po["id"], "warehouse": str(wh.id),
            "items": [{"purchase_order_item": po_item_id, "product": str(product.id),
                       "quantity": 8, "unit_cost": 60}],
        }, format="json")

        item = StockItem.objects.get(company=self.company, warehouse=wh, product=product)
        self.assertEqual(item.quantity_on_hand, Decimal("8.000"))
        self.assertEqual(PurchaseOrder.objects.get(id=po["id"]).status,
                         PurchaseOrder.Status.PARTIALLY_RECEIVED)

    def test_over_receiving_is_blocked(self):
        wh = self.make_warehouse()
        supplier = self.make_supplier()
        product = self.make_product(cost_price="60")
        po = self.client.post("/api/v1/purchase-orders/", {
            "supplier": str(supplier.id),
            "items": [{"product": str(product.id), "quantity": 5, "unit_price": 60}],
        }, format="json").data
        resp = self.client.post("/api/v1/goods-receipts/", {
            "purchase_order": po["id"], "warehouse": str(wh.id),
            "items": [{"purchase_order_item": po["items"][0]["id"], "product": str(product.id),
                       "quantity": 6, "unit_cost": 60}],
        }, format="json")
        self.assertEqual(resp.status_code, 400)
