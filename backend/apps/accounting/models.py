from decimal import Decimal

from django.db import models

from apps.core.models import CompanyScopedModel
from apps.sales.models import PaymentMethod


class Account(CompanyScopedModel):
    """A chart-of-accounts entry. Ledger data (JournalEntryLine) references
    these, never a hardcoded account name, so custom accounts a company adds
    later work the same as the seeded defaults."""

    class AccountType(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, related_name="children", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def is_debit_normal(self) -> bool:
        return self.account_type in (Account.AccountType.ASSET, Account.AccountType.EXPENSE)


class JournalEntry(CompanyScopedModel):
    """A balanced set of debit/credit lines. Created either directly (manual
    entries) or by `apps.accounting.services` on business events elsewhere
    in the system (invoice confirmed, goods received, POS sale, ...)."""

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        INVOICE = "invoice", "Invoice"
        SALES_PAYMENT = "sales_payment", "Sales payment"
        GOODS_RECEIPT = "goods_receipt", "Goods receipt"
        PURCHASE_PAYMENT = "purchase_payment", "Purchase payment"
        POS_SALE = "pos_sale", "POS sale"
        POS_REFUND = "pos_refund", "POS refund"
        EXPENSE = "expense", "Expense"

    number = models.CharField(max_length=30)
    entry_date = models.DateField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        unique_together = ("company", "number")
        ordering = ["-entry_date", "-created_at"]
        verbose_name_plural = "journal entries"

    def __str__(self):
        return self.number


class JournalEntryLine(CompanyScopedModel):
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="lines")
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["id"]


class ExpenseCategory(CompanyScopedModel):
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("company", "name")
        verbose_name_plural = "expense categories"

    def __str__(self):
        return self.name


class Expense(CompanyScopedModel):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, related_name="expenses", null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    expense_date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, related_name="+", null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.description or self.category} - {self.amount}"
