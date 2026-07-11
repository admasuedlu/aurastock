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

from django.conf import settings
from django.core.exceptions import ValidationError


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


PROVIDERS = {p.name: p for p in [SandboxProvider()]}


def get_provider(name: str) -> PaymentProvider:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValidationError(f"Unknown payment provider: {name}.")
