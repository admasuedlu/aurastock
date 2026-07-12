from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.test_utils import TenantAPITestCase
from apps.tenants.models import Company, SubscriptionPlan


class PlatformAdminTests(TenantAPITestCase):
    """self.client is a tenant owner; self.admin_client is a platform operator
    (a User with no company + is_staff), which IsPlatformAdmin gates on."""

    def setUp(self):
        super().setUp()
        admin = get_user_model().objects.create_user(
            username="platadmin", email="admin@saas.test", password="AdminPass123!",
            company=None, is_staff=True,
        )
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=admin)

    def test_tenant_user_is_denied_platform_endpoints(self):
        self.assertEqual(self.client.get("/api/v1/platform/overview/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/platform/companies/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/v1/platform/plans/", {"name": "X", "code": "x"}, format="json").status_code, 403)

    def test_platform_admin_sees_overview_and_company_usage(self):
        self.assertEqual(self.admin_client.get("/api/v1/platform/overview/").status_code, 200)
        companies = self.admin_client.get("/api/v1/platform/companies/").data
        row = next(r for r in companies["results"] if r["id"] == str(self.company.id))
        self.assertEqual(row["user_count"], 1)  # just the seeded owner

    def test_suspend_then_activate_company(self):
        suspend = self.admin_client.post(f"/api/v1/platform/companies/{self.company.id}/suspend/")
        self.assertEqual(suspend.status_code, 200)
        self.assertEqual(Company.objects.get(id=self.company.id).subscription_status,
                         Company.SubscriptionStatus.SUSPENDED)

        activate = self.admin_client.post(f"/api/v1/platform/companies/{self.company.id}/activate/")
        self.assertEqual(activate.status_code, 200)
        self.assertEqual(Company.objects.get(id=self.company.id).subscription_status,
                         Company.SubscriptionStatus.ACTIVE)

    def test_change_plan(self):
        starter = SubscriptionPlan.objects.create(name="Starter", code="starter",
                                                  max_users=5, max_warehouses=5)
        resp = self.admin_client.post(f"/api/v1/platform/companies/{self.company.id}/change-plan/",
                                     {"plan": str(starter.id)}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Company.objects.get(id=self.company.id).subscription_plan_id, starter.id)

    def test_plan_crud_by_admin(self):
        create = self.admin_client.post("/api/v1/platform/plans/", {
            "name": "Business", "code": "business",
            "max_users": 20, "max_branches": 5, "max_warehouses": 10,
        }, format="json")
        self.assertEqual(create.status_code, 201)
        listing = self.admin_client.get("/api/v1/platform/plans/").data
        self.assertTrue(any(p["code"] == "business" for p in listing["results"]))
