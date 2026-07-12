from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.accounting.models import Account, JournalEntry
from apps.accounting.services import close_accounting_period, create_journal_entry
from apps.core.test_utils import TenantAPITestCase


class JournalEntryTests(TenantAPITestCase):
    def _acct(self, code):
        return Account.objects.get(company=self.company, code=code)

    def test_unbalanced_entry_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(company=self.company, lines=[
                {"account": self._acct("1000"), "debit": Decimal("100")},
                {"account": self._acct("4000"), "credit": Decimal("90")},
            ])

    def test_zero_entry_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(company=self.company, lines=[
                {"account": self._acct("1000"), "debit": Decimal("0")},
                {"account": self._acct("4000"), "credit": Decimal("0")},
            ])

    def test_balanced_entry_persists(self):
        entry = create_journal_entry(company=self.company, lines=[
            {"account": self._acct("1000"), "debit": Decimal("100")},
            {"account": self._acct("4000"), "credit": Decimal("100")},
        ])
        self.assertEqual(entry.lines.count(), 2)


class PeriodCloseTests(TenantAPITestCase):
    def _acct(self, code):
        return Account.objects.get(company=self.company, code=code)

    def _balance(self, code):
        acct = self._acct(code)
        totals = {"debit": Decimal("0"), "credit": Decimal("0")}
        for line in acct.lines.all():
            totals["debit"] += line.debit
            totals["credit"] += line.credit
        return (totals["debit"] - totals["credit"]) if acct.is_debit_normal else (totals["credit"] - totals["debit"])

    def test_close_moves_net_income_to_retained_earnings_and_zeros_pl(self):
        # Revenue 500, expense 200 -> net income 300
        create_journal_entry(company=self.company, lines=[
            {"account": self._acct("1100"), "debit": Decimal("500")},
            {"account": self._acct("4000"), "credit": Decimal("500")},
        ])
        create_journal_entry(company=self.company, lines=[
            {"account": self._acct("5100"), "debit": Decimal("200")},
            {"account": self._acct("1000"), "credit": Decimal("200")},
        ])

        entry = close_accounting_period(company=self.company, user=self.user)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.source, JournalEntry.Source.CLOSING)

        # Income & expense accounts are now flat; net income sits in retained earnings.
        self.assertEqual(self._balance("4000"), Decimal("0"))
        self.assertEqual(self._balance("5100"), Decimal("0"))
        self.assertEqual(self._balance("3100"), Decimal("300"))

    def test_close_with_no_activity_returns_none(self):
        self.assertIsNone(close_accounting_period(company=self.company, user=self.user))


class LedgerBalanceEndToEndTests(TenantAPITestCase):
    """Drives a full purchase->pay->invoice->POS cycle through the API and
    asserts every automatic journal entry keeps the trial balance balanced --
    the core double-entry invariant."""

    def test_full_cycle_keeps_trial_balance_balanced(self):
        warehouse = self.make_warehouse()
        supplier = self.make_supplier()
        customer = self.make_customer()
        product = self.make_product(selling_price="100", cost_price="60")

        # Purchase: PO -> receive (Dr Inventory/VAT, Cr AP) -> pay (Dr AP, Cr Cash).
        po = self.client.post("/api/v1/purchase-orders/", {
            "supplier": str(supplier.id),
            "items": [{"product": str(product.id), "quantity": 20, "unit_price": 60}],
        }, format="json").data
        self.client.post("/api/v1/goods-receipts/", {
            "purchase_order": po["id"], "warehouse": str(warehouse.id),
            "items": [{"purchase_order_item": po["items"][0]["id"], "product": str(product.id),
                       "quantity": 20, "unit_cost": 60}],
        }, format="json")
        self.client.post(f"/api/v1/purchase-orders/{po['id']}/record-payment/",
                         {"amount": 690, "method": "bank_transfer"}, format="json")  # 20*60 + 15% VAT

        # Sale: invoice -> confirm (Dr AR, Cr Revenue+VAT, Dr COGS/Cr Inventory) -> payment.
        invoice = self.client.post("/api/v1/invoices/", {
            "customer": str(customer.id), "warehouse": str(warehouse.id),
            "items": [{"product": str(product.id), "quantity": 5, "unit_price": 100}],
        }, format="json").data
        self.client.post(f"/api/v1/invoices/{invoice['id']}/confirm/", {}, format="json")
        self.client.post(f"/api/v1/invoices/{invoice['id']}/record-payment/",
                         {"amount": 100, "method": "cash"}, format="json")

        # POS: sale then refund (mirrored pairs).
        session = self.client.post("/api/v1/pos-sessions/",
                                  {"warehouse": str(warehouse.id), "opening_cash": 0}, format="json").data
        sale = self.client.post("/api/v1/pos-transactions/", {
            "session": session["id"], "payment_method": "cash", "amount_tendered": 500,
            "items": [{"product": str(product.id), "quantity": 3, "unit_price": 100}],
        }, format="json").data
        self.client.post(f"/api/v1/pos-transactions/{sale['id']}/refund/", {}, format="json")

        # Manual expense (Dr Operating Expenses, Cr Cash).
        self.client.post("/api/v1/accounting/expenses/",
                         {"amount": 40, "payment_method": "cash", "description": "Stationery"}, format="json")

        tb = self.client.get("/api/v1/accounting/reports/trial-balance/").data
        self.assertTrue(tb["is_balanced"])
        self.assertEqual(tb["total_debit"], tb["total_credit"])
