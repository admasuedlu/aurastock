from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.test_utils import TenantAPITestCase


class RolePermissionTests(TenantAPITestCase):
    """The setUp user is the company Owner (all permissions). These tests point
    fresh clients at limited starter roles and assert the module.action gate."""

    def setUp(self):
        super().setUp()
        self.customer = self.make_customer()
        self.supplier = self.make_supplier()
        self.product = self.make_product()

    def _client_as(self, role_name):
        client = APIClient()
        self.make_user_with_role(role_name, client)
        return client

    def _quotation_payload(self):
        return {"customer": str(self.customer.id),
                "items": [{"product": str(self.product.id), "quantity": 1, "unit_price": 100}]}

    def test_sales_person_can_create_quotation(self):
        resp = self._client_as("Sales Person").post("/api/v1/quotations/", self._quotation_payload(), format="json")
        self.assertEqual(resp.status_code, 201)

    def test_sales_person_cannot_create_expense_or_po(self):
        client = self._client_as("Sales Person")
        expense = client.post("/api/v1/accounting/expenses/", {"amount": 50, "payment_method": "cash"}, format="json")
        self.assertEqual(expense.status_code, 403)
        po = client.post("/api/v1/purchase-orders/", {
            "supplier": str(self.supplier.id),
            "items": [{"product": str(self.product.id), "quantity": 1, "unit_price": 10}],
        }, format="json")
        self.assertEqual(po.status_code, 403)

    def test_accountant_can_expense_but_not_quote(self):
        client = self._client_as("Accountant")
        expense = client.post("/api/v1/accounting/expenses/",
                              {"amount": 50, "payment_method": "cash", "description": "Rent"}, format="json")
        self.assertEqual(expense.status_code, 201)
        # Accountant has sales *view* only -> can read invoices but not create quotations.
        self.assertEqual(client.get("/api/v1/invoices/").status_code, 200)
        self.assertEqual(client.post("/api/v1/quotations/", self._quotation_payload(), format="json").status_code, 403)

    def test_only_approver_role_can_approve_purchase_request(self):
        procurement = self._client_as("Procurement Officer")
        pr = procurement.post("/api/v1/purchase-requests/", {
            "items": [{"product": str(self.product.id), "quantity": 1, "unit_price": 10}],
        }, format="json").data
        procurement.post(f"/api/v1/purchase-requests/{pr['id']}/submit/", {}, format="json")

        # A Sales Person has no purchase permissions at all -> approve is refused.
        sales = self._client_as("Sales Person")
        self.assertEqual(
            sales.post(f"/api/v1/purchase-requests/{pr['id']}/approve/", {}, format="json").status_code, 403)
        # The Procurement Officer holds purchases.approve.
        self.assertEqual(
            procurement.post(f"/api/v1/purchase-requests/{pr['id']}/approve/", {}, format="json").status_code, 200)

    def test_cashier_can_open_session_but_not_expense(self):
        client = self._client_as("Cashier")
        warehouse = self.make_warehouse()
        session = client.post("/api/v1/pos-sessions/",
                             {"warehouse": str(warehouse.id), "opening_cash": 100}, format="json")
        self.assertEqual(session.status_code, 201)
        self.assertEqual(
            client.post("/api/v1/accounting/expenses/", {"amount": 10, "payment_method": "cash"}, format="json").status_code,
            403)

    def test_user_with_no_role_is_denied_guarded_endpoints(self):
        User = get_user_model()
        user = User.objects.create_user(username="norole", email="norole@example.test",
                                        password="x", company=self.company, role=None)
        client = APIClient()
        client.force_authenticate(user=user)
        self.assertEqual(client.get("/api/v1/products/").status_code, 403)

    def test_manual_stock_in_requires_inventory_permission(self):
        warehouse = self.make_warehouse()
        payload = {"warehouse": str(warehouse.id), "product": str(self.product.id),
                   "quantity": 5, "unit_cost": 10}
        # Sales Person has no inventory permission.
        self.assertEqual(
            self._client_as("Sales Person").post("/api/v1/inventory/stock-in/", payload, format="json").status_code,
            403)
        # Inventory Manager does.
        self.assertEqual(
            self._client_as("Inventory Manager").post("/api/v1/inventory/stock-in/", payload, format="json").status_code,
            201)


class LoginThrottleTests(TenantAPITestCase):
    def test_repeated_login_attempts_are_rate_limited(self):
        # Default cap is 10/min per IP; the 11th attempt from one client is 429,
        # regardless of whether the credentials are valid (throttled before auth).
        client = APIClient()
        statuses = [
            client.post("/api/v1/auth/token/",
                        {"email": "bruteforce@example.test", "password": "guess"}, format="json").status_code
            for _ in range(12)
        ]
        self.assertEqual(statuses[-1], 429)
        self.assertIn(429, statuses)
        self.assertLessEqual(statuses.count(429), 2)  # only the last couple, not all

    def test_portal_login_shares_the_same_limit(self):
        client = APIClient()
        for _ in range(11):
            last = client.post("/api/v1/portal/login/",
                               {"email": "x@portal.test", "password": "guess"}, format="json")
        self.assertEqual(last.status_code, 429)
