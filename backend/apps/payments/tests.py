import json

from apps.core.test_utils import TenantAPITestCase
from apps.payments.models import PaymentIntent
from apps.payments.providers import SandboxProvider
from apps.sales.models import Invoice, SalesPayment


class PaymentGatewayTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        wh = self.make_warehouse()
        customer = self.make_customer()
        product = self.make_product(selling_price="100")
        self.receive_stock(product, wh, 10, unit_cost="60")
        invoice = self.client.post("/api/v1/invoices/", {
            "customer": str(customer.id), "warehouse": str(wh.id),
            "items": [{"product": str(product.id), "quantity": 1, "unit_price": 100, "tax_percent": 0}],
        }, format="json").data
        self.client.post(f"/api/v1/invoices/{invoice['id']}/confirm/", {}, format="json")
        self.invoice_id = invoice["id"]  # total 100, confirmed, balance 100

    def _create_intent(self, amount=None):
        payload = {"invoice": self.invoice_id, "method": "telebirr"}
        if amount is not None:
            payload["amount"] = amount
        return self.client.post("/api/v1/payment-intents/", payload, format="json")

    def test_create_intent_returns_checkout_url(self):
        resp = self._create_intent()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], "pending")
        self.assertEqual(resp.data["amount"], "100.00")
        self.assertTrue(resp.data["checkout_url"].startswith("https://sandbox.aurastock.local/checkout/"))
        self.assertTrue(resp.data["reference"])

    def test_cannot_create_intent_for_draft_invoice(self):
        # A fresh unconfirmed invoice.
        wh = self.make_warehouse(code="WH2", name="Second")
        customer = self.make_customer(name="Beta")
        product = self.make_product(name="Gadget", sku="G-1", selling_price="50")
        draft = self.client.post("/api/v1/invoices/", {
            "customer": str(customer.id), "warehouse": str(wh.id),
            "items": [{"product": str(product.id), "quantity": 1, "unit_price": 50}],
        }, format="json").data
        resp = self.client.post("/api/v1/payment-intents/",
                                {"invoice": draft["id"], "method": "telebirr"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_amount_over_balance_rejected(self):
        self.assertEqual(self._create_intent(amount=150).status_code, 400)

    def test_simulate_callback_records_payment_and_pays_invoice(self):
        intent = self._create_intent().data
        resp = self.client.post(f"/api/v1/payment-intents/{intent['id']}/simulate-callback/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "succeeded")

        self.assertEqual(Invoice.objects.get(id=self.invoice_id).status, Invoice.Status.PAID)
        payment = SalesPayment.objects.get(invoice_id=self.invoice_id)
        self.assertEqual(payment.method, "telebirr")
        self.assertEqual(PaymentIntent.objects.get(id=intent["id"]).sales_payment_id, payment.id)

    def test_simulate_callback_is_idempotent(self):
        intent = self._create_intent().data
        url = f"/api/v1/payment-intents/{intent['id']}/simulate-callback/"
        self.client.post(url, {}, format="json")
        self.client.post(url, {}, format="json")  # again
        # Exactly one payment despite two callbacks.
        self.assertEqual(SalesPayment.objects.filter(invoice_id=self.invoice_id).count(), 1)

    def test_partial_intent_leaves_invoice_partially_paid(self):
        intent = self._create_intent(amount=40).data
        self.client.post(f"/api/v1/payment-intents/{intent['id']}/simulate-callback/", {}, format="json")
        self.assertEqual(Invoice.objects.get(id=self.invoice_id).status, Invoice.Status.PARTIALLY_PAID)

    # --- webhook (the real provider entry point) ---

    def _webhook(self, reference, status="succeeded", sign=True):
        body = json.dumps({"reference": reference, "status": status,
                           "external_reference": "TELE-123"}).encode()
        headers = {}
        if sign:
            headers["HTTP_X_SANDBOX_SIGNATURE"] = SandboxProvider().sign(body)
        return self.client.post("/api/v1/payments/webhook/sandbox/", data=body,
                                content_type="application/json", **headers)

    def test_webhook_with_valid_signature_confirms(self):
        intent = self._create_intent().data
        resp = self._webhook(intent["reference"])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "succeeded")
        self.assertEqual(Invoice.objects.get(id=self.invoice_id).status, Invoice.Status.PAID)
        self.assertEqual(PaymentIntent.objects.get(id=intent["id"]).external_reference, "TELE-123")

    def test_webhook_with_bad_signature_is_rejected(self):
        intent = self._create_intent().data
        resp = self._webhook(intent["reference"], sign=False)
        self.assertEqual(resp.status_code, 400)
        # Nothing was recorded.
        self.assertEqual(PaymentIntent.objects.get(id=intent["id"]).status, "pending")
        self.assertEqual(SalesPayment.objects.filter(invoice_id=self.invoice_id).count(), 0)

    def test_webhook_unknown_reference_is_rejected(self):
        self.assertEqual(self._webhook("does-not-exist").status_code, 400)
