from rest_framework.test import APIClient

from apps.core.test_utils import TenantAPITestCase, make_company
from apps.customers.models import Customer
from apps.portal.models import PortalAccount
from apps.portal.tokens import issue_portal_token
from apps.purchasing.models import PurchaseOrder
from apps.sales.models import Quotation


class PortalTests(TenantAPITestCase):
    def setUp(self):
        super().setUp()
        self.customer = self.make_customer()
        self.supplier = self.make_supplier()
        self.cust_account = self._account(customer=self.customer, email="cust@portal.test")
        self.supp_account = self._account(supplier=self.supplier, email="supp@portal.test")

    def _account(self, email, customer=None, supplier=None):
        account = PortalAccount(company=self.company, customer=customer, supplier=supplier, email=email)
        account.set_password("PortalPass123!")
        account.save()
        return account

    def _portal_client(self, account):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Portal {issue_portal_token(account)}")
        return client

    # --- auth ---

    def test_login_returns_token(self):
        resp = APIClient().post("/api/v1/portal/login/",
                               {"email": "cust@portal.test", "password": "PortalPass123!"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["token"])
        self.assertEqual(resp.data["account_type"], "customer")

    def test_login_wrong_password_rejected(self):
        resp = APIClient().post("/api/v1/portal/login/",
                               {"email": "cust@portal.test", "password": "nope"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_garbage_token_rejected(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Portal not.a.real.token")
        # A bad Portal token raises AuthenticationFailed; DRF renders it 403 here
        # (the authenticator sets no WWW-Authenticate header). Either way: rejected.
        self.assertIn(client.get("/api/v1/portal/quotations/").status_code, (401, 403))

    # --- visibility + actions ---

    def test_customer_sees_sent_not_draft_quotations(self):
        Quotation.objects.create(company=self.company, customer=self.customer,
                                 number="QUO-SENT", status=Quotation.Status.SENT)
        Quotation.objects.create(company=self.company, customer=self.customer,
                                 number="QUO-DRAFT", status=Quotation.Status.DRAFT)
        resp = self._portal_client(self.cust_account).get("/api/v1/portal/quotations/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({r["number"] for r in resp.data["results"]}, {"QUO-SENT"})

    def test_customer_accepts_sent_quotation_exactly_once(self):
        quote = Quotation.objects.create(company=self.company, customer=self.customer,
                                         number="QUO-A", status=Quotation.Status.SENT)
        client = self._portal_client(self.cust_account)
        first = client.post(f"/api/v1/portal/quotations/{quote.id}/accept/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(Quotation.objects.get(id=quote.id).status, Quotation.Status.ACCEPTED)
        # A second accept is refused (no longer in `sent`).
        self.assertEqual(client.post(f"/api/v1/portal/quotations/{quote.id}/accept/").status_code, 400)

    def test_supplier_acknowledges_sent_po(self):
        po = PurchaseOrder.objects.create(company=self.company, supplier=self.supplier,
                                          number="PO-1", status=PurchaseOrder.Status.SENT)
        resp = self._portal_client(self.supp_account).post(f"/api/v1/portal/purchase-orders/{po.id}/acknowledge/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PurchaseOrder.objects.get(id=po.id).status, PurchaseOrder.Status.APPROVED)

    # --- cross-auth security matrix ---

    def test_customer_token_rejected_on_supplier_endpoint(self):
        self.assertEqual(
            self._portal_client(self.cust_account).get("/api/v1/portal/purchase-orders/").status_code, 403)

    def test_portal_token_rejected_on_staff_endpoint(self):
        resp = self._portal_client(self.cust_account).get("/api/v1/products/")
        self.assertIn(resp.status_code, (401, 403))

    def test_staff_user_rejected_on_portal_endpoint(self):
        # self.client is force-authenticated as the owner (a User, not a PortalAccount).
        self.assertEqual(self.client.get("/api/v1/portal/quotations/").status_code, 403)

    def test_cross_tenant_isolation(self):
        other_company, _ = make_company("Other Co")
        other_customer = Customer.objects.create(company=other_company, name="Other Cust")
        other_account = PortalAccount(company=other_company, customer=other_customer, email="other@portal.test")
        other_account.set_password("PortalPass123!")
        other_account.save()
        Quotation.objects.create(company=self.company, customer=self.customer,
                                 number="QUO-T1", status=Quotation.Status.SENT)
        resp = self._portal_client(other_account).get("/api/v1/portal/quotations/")
        self.assertEqual(resp.data["count"], 0)
