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
