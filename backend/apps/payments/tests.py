import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import override_settings

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


@override_settings(
    CHAPA_SECRET_KEY="CHASECK_TEST-abc",
    CHAPA_WEBHOOK_SECRET="whsec-test",
    CHAPA_BASE_URL="https://api.chapa.co/v1",
)
class ChapaGatewayTests(TenantAPITestCase):
    """Exercises the Chapa provider end to end with the outbound HTTP call
    mocked, so the initialize -> webhook -> recorded-payment flow is verified
    without needing live Chapa credentials."""

    _FAKE_INIT = {
        "status": "success",
        "data": {"checkout_url": "https://checkout.chapa.co/checkout/payment/abc123"},
    }

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

    def _create_chapa_intent(self):
        with patch("apps.payments.providers._http_post_json", return_value=self._FAKE_INIT) as mock_post:
            resp = self.client.post("/api/v1/payment-intents/", {
                "invoice": self.invoice_id, "method": "telebirr", "provider": "chapa",
            }, format="json")
        return resp, mock_post

    def test_create_chapa_intent_initializes_and_returns_checkout(self):
        resp, mock_post = self._create_chapa_intent()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["provider"], "chapa")
        self.assertEqual(resp.data["checkout_url"], "https://checkout.chapa.co/checkout/payment/abc123")

        url, headers, payload = mock_post.call_args.args
        self.assertTrue(url.endswith("/transaction/initialize"))
        self.assertEqual(payload["currency"], "ETB")
        self.assertEqual(payload["tx_ref"], resp.data["reference"])
        self.assertEqual(headers["Authorization"], "Bearer CHASECK_TEST-abc")

    def _chapa_webhook(self, tx_ref, status="success", sign=True, secret="whsec-test"):
        body = json.dumps({
            "event": "charge.success", "tx_ref": tx_ref,
            "status": status, "reference": "CHAPA-REF-1",
        }).encode()
        headers = {}
        if sign:
            headers["HTTP_X_CHAPA_SIGNATURE"] = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return self.client.post("/api/v1/payments/webhook/chapa/", data=body,
                                content_type="application/json", **headers)

    def test_chapa_webhook_confirms_payment(self):
        intent = self._create_chapa_intent()[0].data
        resp = self._chapa_webhook(intent["reference"])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "succeeded")
        self.assertEqual(Invoice.objects.get(id=self.invoice_id).status, Invoice.Status.PAID)
        payment = SalesPayment.objects.get(invoice_id=self.invoice_id)
        self.assertEqual(payment.method, "telebirr")
        self.assertEqual(PaymentIntent.objects.get(id=intent["id"]).sales_payment_id, payment.id)

    def test_chapa_webhook_bad_signature_is_rejected(self):
        intent = self._create_chapa_intent()[0].data
        resp = self._chapa_webhook(intent["reference"], sign=False)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(PaymentIntent.objects.get(id=intent["id"]).status, "pending")
        self.assertEqual(SalesPayment.objects.filter(invoice_id=self.invoice_id).count(), 0)

    def test_chapa_webhook_wrong_secret_is_rejected(self):
        intent = self._create_chapa_intent()[0].data
        resp = self._chapa_webhook(intent["reference"], secret="not-the-secret")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SalesPayment.objects.filter(invoice_id=self.invoice_id).count(), 0)
