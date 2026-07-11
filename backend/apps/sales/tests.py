from decimal import Decimal

from apps.accounting.models import Account, JournalEntryLine
from apps.core.test_utils import TenantAPITestCase
from apps.inventory.models import StockItem
from apps.sales.models import Invoice, Quotation, SalesOrder


class QuotationToOrderTests(TenantAPITestCase):
    def _quotation_payload(self, customer, product):
        return {
            "customer": str(customer.id),
            "items": [{"product": str(product.id), "quantity": 3, "unit_price": 100}],
        }

    def test_convert_quotation_to_order_copies_items_and_locks_quotation(self):
        customer = self.make_customer()
        product = self.make_product()
        quotation = self.client.post("/api/v1/quotations/", self._quotation_payload(customer, product),
                                     format="json").data
        resp = self.client.post(f"/api/v1/quotations/{quotation['id']}/convert-to-order/", {}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp.data["items"]), 1)
        # Quotation is now locked as converted, and a second conversion is refused.
        self.assertEqual(Quotation.objects.get(id=quotation["id"]).status, Quotation.Status.CONVERTED)
        again = self.client.post(f"/api/v1/quotations/{quotation['id']}/convert-to-order/", {}, format="json")
        self.assertEqual(again.status_code, 400)


class SalesOrderToInvoiceTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.wh = self.make_warehouse()
        self.customer = self.make_customer()
        self.product = self.make_product(selling_price="100")
        self.receive_stock(self.product, self.wh, 100, unit_cost="60")
        order = self.client.post("/api/v1/sales-orders/", {
            "customer": str(self.customer.id),
            "items": [{"product": str(self.product.id), "quantity": 10, "unit_price": 100}],
        }, format="json").data
        self.order_id = order["id"]
        self.line_id = order["items"][0]["id"]

    def _convert(self, quantity=None):
        payload = {"warehouse": str(self.wh.id)}
        if quantity is not None:
            payload["items"] = [{"sales_order_item": self.line_id, "quantity": quantity}]
        return self.client.post(f"/api/v1/sales-orders/{self.order_id}/convert-to-invoice/",
                                payload, format="json")

    def test_partial_invoicing_tracks_outstanding_and_fulfils(self):
        r1 = self._convert(quantity=4)
        self.assertEqual(r1.status_code, 201)
        order = self.client.get(f"/api/v1/sales-orders/{self.order_id}/").data
        self.assertEqual(order["status"], SalesOrder.Status.CONFIRMED)
        self.assertEqual(order["items"][0]["quantity_outstanding"], "6.000")

        self._convert(quantity=4)  # 8 invoiced, 2 left
        self._convert()            # remainder -> fulfilled
        order = self.client.get(f"/api/v1/sales-orders/{self.order_id}/").data
        self.assertEqual(order["status"], SalesOrder.Status.FULFILLED)
        self.assertEqual(order["items"][0]["quantity_outstanding"], "0.000")

    def test_over_invoicing_is_blocked(self):
        resp = self._convert(quantity=11)
        self.assertEqual(resp.status_code, 400)

    def test_fully_invoiced_order_rejects_further_invoicing(self):
        self._convert()  # whole order
        resp = self._convert()
        self.assertEqual(resp.status_code, 400)


class InvoiceConfirmTests(TenantAPITestCase):
    def test_confirm_deducts_stock_and_posts_balanced_cogs(self):
        wh = self.make_warehouse()
        customer = self.make_customer()
        product = self.make_product(selling_price="100")
        self.receive_stock(product, wh, 100, unit_cost="60")

        invoice = self.client.post("/api/v1/invoices/", {
            "customer": str(customer.id), "warehouse": str(wh.id),
            "items": [{"product": str(product.id), "quantity": 5, "unit_price": 100, "tax_percent": 0}],
        }, format="json").data
        resp = self.client.post(f"/api/v1/invoices/{invoice['id']}/confirm/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], Invoice.Status.CONFIRMED)

        # Stock deducted
        item = StockItem.objects.get(company=self.company, warehouse=wh, product=product)
        self.assertEqual(item.quantity_on_hand, Decimal("95.000"))

        # COGS posted: 5 units * 60 = 300 on account 5000, and the journal balances
        cogs = Account.objects.get(company=self.company, code="5000")
        cogs_debit = sum((line.debit for line in JournalEntryLine.objects.filter(
            company=self.company, account=cogs)), Decimal("0"))
        self.assertEqual(cogs_debit, Decimal("300.00"))

    def test_cannot_confirm_twice(self):
        wh = self.make_warehouse()
        customer = self.make_customer()
        product = self.make_product()
        self.receive_stock(product, wh, 10, unit_cost="60")
        invoice = self.client.post("/api/v1/invoices/", {
            "customer": str(customer.id), "warehouse": str(wh.id),
            "items": [{"product": str(product.id), "quantity": 2, "unit_price": 100}],
        }, format="json").data
        self.client.post(f"/api/v1/invoices/{invoice['id']}/confirm/", {}, format="json")
        again = self.client.post(f"/api/v1/invoices/{invoice['id']}/confirm/", {}, format="json")
        self.assertEqual(again.status_code, 400)
