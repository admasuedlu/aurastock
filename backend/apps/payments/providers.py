"""Payment-provider abstraction. A real gateway (Telebirr, CBE Pay, Stripe, ...)
is added by writing one PaymentProvider subclass and registering it in
PROVIDERS -- the intent/confirm/webhook flow in services.py stays the same.

Only a sandbox provider is implemented here: there are no live merchant
credentials or a public callback URL in this environment, so a real gateway
can't be exercised. The sandbox mints a fake checkout URL and verifies webhooks
with an HMAC-SHA256 signature exactly the way a real one would, so the flow and
its security are genuinely tested end to end."""
import hashlib
import hmac
import json
import urllib.error
import urllib.request

from django.conf import settings
from django.core.exceptions import ValidationError


def _http_post_json(url: str, headers: dict, payload: dict, timeout: int = 20) -> dict:
    """POST JSON and return the parsed response. Isolated at module level so
    tests can monkeypatch it instead of hitting the network."""
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=data, method="POST",
        headers={**headers, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise ValidationError(f"Payment gateway error {exc.code}: {body[:200]}")
    except urllib.error.URLError as exc:
        raise ValidationError(f"Could not reach the payment gateway: {exc.reason}")


class PaymentProvider:
    name = ""

    def create_checkout(self, intent) -> dict:
        """Return {checkout_url, external_reference} for a fresh intent."""
        raise NotImplementedError

    def parse_webhook(self, headers, body: bytes) -> dict:
        """Verify the callback's authenticity and return
        {reference, status, external_reference}. Raise ValidationError if the
        signature doesn't check out."""
        raise NotImplementedError


class SandboxProvider(PaymentProvider):
    name = "sandbox"

    def _secret(self) -> bytes:
        return settings.PAYMENTS_SANDBOX_SECRET.encode()

    def sign(self, body: bytes) -> str:
        return hmac.new(self._secret(), body, hashlib.sha256).hexdigest()

    def create_checkout(self, intent) -> dict:
        return {
            "checkout_url": f"https://sandbox.aurastock.local/checkout/{intent.reference}",
            "external_reference": f"SBX-{intent.reference}",
        }

    def parse_webhook(self, headers, body: bytes) -> dict:
        signature = headers.get("X-Sandbox-Signature", "")
        if not hmac.compare_digest(signature, self.sign(body)):
            raise ValidationError("Invalid webhook signature.")
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            raise ValidationError("Malformed webhook body.")
        reference = payload.get("reference")
        if not reference:
            raise ValidationError("Webhook is missing a reference.")
        return {
            "reference": reference,
            "status": payload.get("status", "succeeded"),
            "external_reference": payload.get("external_reference", ""),
        }


class ChapaProvider(PaymentProvider):
    """Chapa (https://chapa.co) -- Ethiopia's payment aggregator, which fronts
    Telebirr, CBE Birr, mobile money, and cards behind one hosted checkout.

    create_checkout initializes a transaction and hands back Chapa's hosted
    checkout URL; parse_webhook verifies the callback Chapa POSTs when the payer
    finishes. Going live only needs CHAPA_SECRET_KEY (and, ideally,
    CHAPA_WEBHOOK_SECRET) set in the environment -- no code change."""

    name = "chapa"

    def _secret(self) -> str:
        key = settings.CHAPA_SECRET_KEY
        if not key:
            raise ValidationError("Chapa is not configured (CHAPA_SECRET_KEY is empty).")
        return key

    def _webhook_secret(self) -> bytes:
        # A dedicated webhook secret is preferred; fall back to the API key.
        return (settings.CHAPA_WEBHOOK_SECRET or settings.CHAPA_SECRET_KEY).encode()

    def create_checkout(self, intent) -> dict:
        invoice = intent.invoice
        customer = getattr(invoice, "customer", None)
        name = (getattr(customer, "name", "") or "Customer").strip()
        first_name = (name.split()[0] if name else "Customer")[:50]
        last_name = (" ".join(name.split()[1:]) or "-")[:50]
        email = (getattr(customer, "email", "") or "").strip() or settings.CHAPA_DEFAULT_EMAIL

        payload = {
            "amount": str(intent.amount),
            "currency": "ETB",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "tx_ref": intent.reference,
            "callback_url": f"{settings.PAYMENTS_CALLBACK_BASE_URL}/api/v1/payments/webhook/chapa/",
            "return_url": settings.PAYMENTS_RETURN_URL,
            "customization": {"title": "AuraStock", "description": f"Invoice {invoice.number}"[:50]},
        }
        result = _http_post_json(
            f"{settings.CHAPA_BASE_URL}/transaction/initialize",
            {"Authorization": f"Bearer {self._secret()}"},
            payload,
        )
        if (result.get("status") or "").lower() != "success":
            raise ValidationError(f"Chapa rejected the payment: {result.get('message', 'unknown error')}")
        checkout_url = (result.get("data") or {}).get("checkout_url")
        if not checkout_url:
            raise ValidationError("Chapa did not return a checkout URL.")
        return {"checkout_url": checkout_url, "external_reference": intent.reference}

    def _valid_signature(self, headers, body: bytes) -> bool:
        secret = self._webhook_secret()
        # Chapa signs two ways across its docs/versions: HMAC of the request
        # body, and HMAC of the secret with itself. Accept either.
        body_sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
        secret_sig = hmac.new(secret, secret, hashlib.sha256).hexdigest()
        candidates = {
            headers.get("x-chapa-signature", ""),
            headers.get("X-Chapa-Signature", ""),
            headers.get("Chapa-Signature", ""),
        }
        candidates.discard("")
        return any(
            hmac.compare_digest(sig, body_sig) or hmac.compare_digest(sig, secret_sig)
            for sig in candidates
        )

    def parse_webhook(self, headers, body: bytes) -> dict:
        if not self._valid_signature(headers, body):
            raise ValidationError("Invalid Chapa webhook signature.")
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            raise ValidationError("Malformed Chapa webhook body.")
        tx_ref = payload.get("tx_ref")
        if not tx_ref:
            raise ValidationError("Chapa webhook is missing tx_ref.")
        succeeded = (payload.get("status") or "").lower() == "success"
        return {
            "reference": tx_ref,
            "status": "succeeded" if succeeded else "failed",
            "external_reference": payload.get("reference") or payload.get("id") or tx_ref,
        }


PROVIDERS = {p.name: p for p in [SandboxProvider(), ChapaProvider()]}


def get_provider(name: str) -> PaymentProvider:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValidationError(f"Unknown payment provider: {name}.")
