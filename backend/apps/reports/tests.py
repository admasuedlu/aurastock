from apps.core.test_utils import TenantAPITestCase


class ReportsNumbersTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.warehouse = self.make_warehouse()
        self.customer = self.make_customer()

    def _confirmed_invoice(self, product, quantity, unit_price):
        invoice = self.client.post("/api/v1/invoices/", {
            "customer": str(self.customer.id), "warehouse": str(self.warehouse.id),
            "items": [{"product": str(product.id), "quantity": quantity,
                       "unit_price": unit_price, "tax_percent": 0}],
        }, format="json").data
        self.client.post(f"/api/v1/invoices/{invoice['id']}/confirm/", {}, format="json")
        return invoice

    def test_sales_summary_totals(self):
        product = self.make_product(selling_price="100")
        self.receive_stock(product, self.warehouse, 10, unit_cost="60")
        self._confirmed_invoice(product, 3, 100)  # revenue 300, tax 0

        data = self.client.get("/api/v1/reports/sales-summary/").data
        self.assertEqual(float(data["today_total"]), 300.0)
        self.assertEqual(float(data["period_total"]), 300.0)

    def test_top_products_ranked_by_revenue(self):
        alpha = self.make_product(name="Alpha", sku="A-1", selling_price="100")
        bravo = self.make_product(name="Bravo", sku="B-1", selling_price="100")
        for p in (alpha, bravo):
            self.receive_stock(p, self.warehouse, 100, unit_cost="10")
        self._confirmed_invoice(alpha, 8, 100)  # 800
        self._confirmed_invoice(bravo, 2, 100)  # 200

        rows = self.client.get("/api/v1/reports/top-products/").data["rows"]
        self.assertEqual(rows[0]["product_name"], "Alpha")
        self.assertEqual(float(rows[0]["revenue"]), 800.0)
        self.assertEqual(float(rows[1]["revenue"]), 200.0)

    def test_abc_analysis_classes(self):
        products = {
            "Alpha": ("A-1", 800), "Bravo": ("B-1", 150), "Charlie": ("C-1", 50),
        }
        for name, (sku, revenue) in products.items():
            p = self.make_product(name=name, sku=sku, selling_price="1")
            self.receive_stock(p, self.warehouse, 1000, unit_cost="0")
            self._confirmed_invoice(p, revenue, 1)  # revenue == quantity * 1

        data = self.client.get("/api/v1/reports/abc-analysis/").data
        by_name = {r["product_name"]: r for r in data["rows"]}
        self.assertEqual(by_name["Alpha"]["abc_class"], "A")     # cumulative 80%
        self.assertEqual(by_name["Bravo"]["abc_class"], "B")     # cumulative 95%
        self.assertEqual(by_name["Charlie"]["abc_class"], "C")   # cumulative 100%
        self.assertEqual(float(data["total_revenue"]), 1000.0)

    def test_inventory_valuation(self):
        product = self.make_product(selling_price="100")
        self.receive_stock(product, self.warehouse, 10, unit_cost="6")  # value 60
        data = self.client.get("/api/v1/reports/inventory-valuation/").data
        self.assertEqual(float(data["total_value"]), 60.0)

    def test_dead_stock_lists_unsold_on_hand(self):
        product = self.make_product(name="Idle", sku="IDLE-1")
        self.receive_stock(product, self.warehouse, 5, unit_cost="10")  # never sold
        rows = self.client.get("/api/v1/reports/dead-stock/", {"days": 30}).data["rows"]
        self.assertTrue(any(r["product_sku"] == "IDLE-1" for r in rows))

    def test_purchase_summary_counts_goods_receipts(self):
        # Receive against a PO so a GoodsReceipt exists (the purchase report basis).
        supplier = self.make_supplier()
        product = self.make_product(cost_price="60")
        po = self.client.post("/api/v1/purchase-orders/", {
            "supplier": str(supplier.id),
            "items": [{"product": str(product.id), "quantity": 10, "unit_price": 60}],
        }, format="json").data
        self.client.post("/api/v1/goods-receipts/", {
            "purchase_order": po["id"], "warehouse": str(self.warehouse.id),
            "items": [{"purchase_order_item": po["items"][0]["id"], "product": str(product.id),
                       "quantity": 10, "unit_cost": 60}],
        }, format="json")
        data = self.client.get("/api/v1/reports/purchase-summary/").data
        self.assertEqual(float(data["today_total"]), 600.0)  # 10 * 60
