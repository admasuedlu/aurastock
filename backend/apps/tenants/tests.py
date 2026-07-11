from rest_framework.test import APIClient

from apps.core.test_utils import TenantAPITestCase, make_company
from apps.products.models import Product, UnitOfMeasure
from apps.tenants.models import Company


class TenantIsolationTests(TenantAPITestCase):
    def test_cannot_see_or_fetch_another_tenants_records(self):
        # A second company with its own product, created directly.
        other_company, _ = make_company("Other Co")
        other_uom = UnitOfMeasure.objects.create(company=other_company, name="Piece", symbol="pc")
        other_product = Product.objects.create(
            company=other_company, name="Secret", sku="SEC-1", unit=other_uom,
        )
        # My own product, so the list isn't trivially empty.
        self.make_product(name="Mine", sku="MINE-1")

        listing = self.client.get("/api/v1/products/").data
        skus = {row["sku"] for row in listing["results"]}
        self.assertIn("MINE-1", skus)
        self.assertNotIn("SEC-1", skus)

        # Fetching the other tenant's product by id is a 404, not a leak.
        resp = self.client.get(f"/api/v1/products/{other_product.id}/")
        self.assertEqual(resp.status_code, 404)


class PlanLimitTests(TenantAPITestCase):
    def test_trial_plan_caps_warehouses_at_one(self):
        first = self.client.post("/api/v1/warehouses/", {"name": "WH1", "code": "WH1"}, format="json")
        self.assertEqual(first.status_code, 201)
        # Trial plan allows a single warehouse -> the second is refused.
        second = self.client.post("/api/v1/warehouses/", {"name": "WH2", "code": "WH2"}, format="json")
        self.assertEqual(second.status_code, 400)


class SuspensionEnforcementTests(TenantAPITestCase):
    def test_suspended_tenant_token_is_rejected(self):
        client = APIClient()
        token = client.post("/api/v1/auth/token/", {
            "email": self.user.email, "password": "OwnerPass123!",
        }, format="json").data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Works before suspension.
        self.assertEqual(client.get("/api/v1/products/").status_code, 200)

        # Suspend the tenant -> the same live token now 401s at the auth layer.
        self.company.subscription_status = Company.SubscriptionStatus.SUSPENDED
        self.company.save(update_fields=["subscription_status"])
        self.assertEqual(client.get("/api/v1/products/").status_code, 401)
