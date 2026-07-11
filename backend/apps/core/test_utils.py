"""Shared test helpers. Not a test module itself (name isn't test_*), so the
runner won't collect it -- it just provides a tenant-aware base APITestCase and
factory methods the per-app test modules build on."""
from decimal import Decimal

from rest_framework.test import APITestCase

from apps.accounts.serializers import CompanySignupSerializer
from apps.customers.models import Customer
from apps.inventory.models import Warehouse
from apps.inventory.services import stock_in
from apps.products.models import Product, UnitOfMeasure
from apps.suppliers.models import Supplier

_email_seq = 0


def make_company(name="Test Co"):
    """Create a company + owner via the real signup path (so roles, chart of
    accounts, and the trial plan are all seeded exactly as in production)."""
    global _email_seq
    _email_seq += 1
    result = CompanySignupSerializer().create({
        "company_name": name,
        "owner_first_name": "Owner",
        "owner_last_name": "",
        "owner_email": f"owner{_email_seq}@example.test",
        "owner_phone": "",
        "password": "OwnerPass123!",
    })
    return result["company"], result["user"]


class TenantAPITestCase(APITestCase):
    """Base for tenant-scoped API tests: a fresh company + authenticated owner,
    plus factory helpers. Uses force_authenticate to exercise the views without
    minting a JWT each time."""

    def setUp(self):
        self.company, self.user = make_company()
        self.client.force_authenticate(user=self.user)
        self.uom = UnitOfMeasure.objects.create(company=self.company, name="Piece", symbol="pc")

    # --- factories (via the ORM, so they bypass API-level plan limits) ---

    def make_warehouse(self, code="WH1", name="Main WH"):
        return Warehouse.objects.create(company=self.company, name=name, code=code)

    def make_product(self, name="Widget", sku="SKU-1", selling_price="100",
                     cost_price="0", **flags):
        return Product.objects.create(
            company=self.company, name=name, sku=sku, unit=self.uom,
            cost_price=Decimal(cost_price), selling_price=Decimal(selling_price), **flags,
        )

    def make_customer(self, name="Acme Corp"):
        return Customer.objects.create(company=self.company, name=name)

    def make_supplier(self, name="Global Parts"):
        return Supplier.objects.create(company=self.company, name=name)

    def make_user_with_role(self, role_name, client=None):
        """Create an extra user in this company with one of the seeded starter
        roles, and (optionally) point an APIClient at them. Returns the user."""
        from django.contrib.auth import get_user_model

        from apps.accounts.models import Role

        User = get_user_model()
        role = Role.objects.get(company=self.company, name=role_name)
        global _email_seq
        _email_seq += 1
        user = User.objects.create_user(
            username=f"{role_name.lower().replace(' ', '')}{_email_seq}",
            email=f"staff{_email_seq}@example.test", password="StaffPass123!",
            company=self.company, role=role,
        )
        if client is not None:
            client.force_authenticate(user=user)
        return user

    def receive_stock(self, product, warehouse, quantity, unit_cost="60", **kwargs):
        """Put stock on hand via the inventory service (handles batches too)."""
        return stock_in(
            company=self.company, warehouse=warehouse, product=product,
            quantity=Decimal(str(quantity)), unit_cost=Decimal(str(unit_cost)),
            reference="TEST", reason="test seed", user=self.user, **kwargs,
        )
