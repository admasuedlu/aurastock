from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.core.numbering import next_value

from .models import Account, Expense, JournalEntry, JournalEntryLine

DEFAULT_ACCOUNTS = [
    ("1000", "Cash", Account.AccountType.ASSET),
    ("1010", "Bank", Account.AccountType.ASSET),
    ("1100", "Accounts Receivable", Account.AccountType.ASSET),
    ("1200", "Inventory", Account.AccountType.ASSET),
    ("1300", "VAT Receivable", Account.AccountType.ASSET),
    ("2000", "Accounts Payable", Account.AccountType.LIABILITY),
    ("2100", "VAT Payable", Account.AccountType.LIABILITY),
    ("2200", "Withholding Tax Payable", Account.AccountType.LIABILITY),
    ("3000", "Owner's Equity", Account.AccountType.EQUITY),
    ("3100", "Retained Earnings", Account.AccountType.EQUITY),
    ("4000", "Sales Revenue", Account.AccountType.INCOME),
    ("5000", "Cost of Goods Sold", Account.AccountType.EXPENSE),
    ("5100", "Operating Expenses", Account.AccountType.EXPENSE),
]


def seed_default_chart_of_accounts(company) -> dict[str, Account]:
    accounts = {}
    for code, name, account_type in DEFAULT_ACCOUNTS:
        account, _ = Account.objects.get_or_create(
            company=company, code=code, defaults={"name": name, "account_type": account_type},
        )
        accounts[code] = account
    return accounts


def _get_accounts(company) -> dict[str, Account]:
    return {a.code: a for a in Account.objects.filter(company=company)}


def _cash_or_bank_code(payment_method: str) -> str:
    return "1000" if payment_method == "cash" else "1010"


@transaction.atomic
def create_journal_entry(*, company, lines, description="", reference="", source="manual", user=None) -> JournalEntry:
    total_debit = sum((line.get("debit", Decimal("0")) for line in lines), Decimal("0"))
    total_credit = sum((line.get("credit", Decimal("0")) for line in lines), Decimal("0"))
    if total_debit != total_credit:
        raise ValidationError(f"Journal entry does not balance: debits {total_debit} != credits {total_credit}.")
    if total_debit == 0:
        raise ValidationError("Journal entry must have a non-zero amount.")

    entry = JournalEntry.objects.create(
        company=company, reference=reference, description=description, source=source, created_by=user,
        number=next_value(company, "journal_entry", default_prefix="JE-"),
    )
    JournalEntryLine.objects.bulk_create([
        JournalEntryLine(
            company=company, journal_entry=entry, account=line["account"],
            debit=line.get("debit", Decimal("0")), credit=line.get("credit", Decimal("0")),
            description=line.get("description", ""),
        )
        for line in lines
    ])
    return entry


def record_invoice_confirmed(invoice, cogs_amount: Decimal = Decimal("0")) -> JournalEntry:
    accounts = _get_accounts(invoice.company)
    lines = [
        {"account": accounts["1100"], "debit": invoice.total, "description": invoice.number},
        {"account": accounts["4000"], "credit": invoice.subtotal, "description": invoice.number},
    ]
    if invoice.tax_total:
        lines.append({"account": accounts["2100"], "credit": invoice.tax_total, "description": "VAT"})
    if cogs_amount:
        # Perpetual inventory: the same moment revenue is recognized, the
        # goods' cost basis (from stock_out's weighted-average at time of
        # deduction) moves out of Inventory and into COGS.
        lines.append({"account": accounts["5000"], "debit": cogs_amount, "description": f"COGS {invoice.number}"})
        lines.append({"account": accounts["1200"], "credit": cogs_amount, "description": f"COGS {invoice.number}"})
    return create_journal_entry(
        company=invoice.company, lines=lines, description=f"Invoice {invoice.number} confirmed",
        reference=invoice.number, source=JournalEntry.Source.INVOICE, user=invoice.created_by,
    )


def record_sales_payment(payment, invoice) -> JournalEntry:
    accounts = _get_accounts(payment.company)
    cash_or_bank = accounts[_cash_or_bank_code(payment.method)]
    lines = [
        {"account": cash_or_bank, "debit": payment.amount, "description": invoice.number},
        {"account": accounts["1100"], "credit": payment.amount, "description": invoice.number},
    ]
    return create_journal_entry(
        company=payment.company, lines=lines, description=f"Payment received for {invoice.number}",
        reference=invoice.number, source=JournalEntry.Source.SALES_PAYMENT, user=payment.created_by,
    )


def record_goods_receipt(receipt, total_cost: Decimal, total_tax: Decimal = Decimal("0")) -> JournalEntry:
    """Dr Inventory for the tax-exclusive cost, Dr VAT Receivable for the
    recoverable input tax, Cr Accounts Payable for the tax-inclusive amount
    actually owed to the supplier -- so AP matches what a later PO payment
    for the full invoice amount actually settles."""
    accounts = _get_accounts(receipt.company)
    lines = [
        {"account": accounts["1200"], "debit": total_cost, "description": receipt.number},
        {"account": accounts["2000"], "credit": total_cost + total_tax, "description": receipt.number},
    ]
    if total_tax:
        lines.append({"account": accounts["1300"], "debit": total_tax, "description": "Input VAT"})
    return create_journal_entry(
        company=receipt.company, lines=lines, description=f"Goods receipt {receipt.number}",
        reference=receipt.number, source=JournalEntry.Source.GOODS_RECEIPT, user=receipt.created_by,
    )


def record_purchase_payment(payment, order) -> JournalEntry:
    accounts = _get_accounts(payment.company)
    cash_or_bank = accounts[_cash_or_bank_code(payment.method)]
    lines = [
        {"account": accounts["2000"], "debit": payment.amount, "description": order.number},
        {"account": cash_or_bank, "credit": payment.amount, "description": order.number},
    ]
    return create_journal_entry(
        company=payment.company, lines=lines, description=f"Payment made for {order.number}",
        reference=order.number, source=JournalEntry.Source.PURCHASE_PAYMENT, user=payment.created_by,
    )


def record_pos_sale(pos_transaction, cogs_amount: Decimal = Decimal("0")) -> JournalEntry:
    accounts = _get_accounts(pos_transaction.company)
    cash_or_bank = accounts[_cash_or_bank_code(pos_transaction.payment_method)]
    lines = [
        {"account": cash_or_bank, "debit": pos_transaction.total, "description": pos_transaction.number},
        {"account": accounts["4000"], "credit": pos_transaction.subtotal, "description": pos_transaction.number},
    ]
    if pos_transaction.tax_total:
        lines.append({"account": accounts["2100"], "credit": pos_transaction.tax_total, "description": "VAT"})
    if cogs_amount:
        lines.append({"account": accounts["5000"], "debit": cogs_amount, "description": f"COGS {pos_transaction.number}"})
        lines.append({"account": accounts["1200"], "credit": cogs_amount, "description": f"COGS {pos_transaction.number}"})
    return create_journal_entry(
        company=pos_transaction.company, lines=lines, description=f"POS sale {pos_transaction.number}",
        reference=pos_transaction.number, source=JournalEntry.Source.POS_SALE, user=pos_transaction.created_by,
    )


def record_pos_refund(pos_transaction, user=None, cogs_amount: Decimal = Decimal("0")) -> JournalEntry:
    accounts = _get_accounts(pos_transaction.company)
    cash_or_bank = accounts[_cash_or_bank_code(pos_transaction.payment_method)]
    lines = [
        {"account": accounts["4000"], "debit": pos_transaction.subtotal, "description": pos_transaction.number},
        {"account": cash_or_bank, "credit": pos_transaction.total, "description": pos_transaction.number},
    ]
    if pos_transaction.tax_total:
        lines.append({"account": accounts["2100"], "debit": pos_transaction.tax_total, "description": "VAT reversal"})
    if cogs_amount:
        # Mirrors the sale's COGS lines: the stock the refund view just put
        # back (at its original cost basis) moves back from COGS to Inventory.
        lines.append({"account": accounts["1200"], "debit": cogs_amount, "description": f"COGS reversal {pos_transaction.number}"})
        lines.append({"account": accounts["5000"], "credit": cogs_amount, "description": f"COGS reversal {pos_transaction.number}"})
    return create_journal_entry(
        company=pos_transaction.company, lines=lines, description=f"POS refund {pos_transaction.number}",
        reference=pos_transaction.number, source=JournalEntry.Source.POS_REFUND, user=user,
    )


def record_expense(expense: Expense) -> JournalEntry:
    accounts = _get_accounts(expense.company)
    cash_or_bank = accounts[_cash_or_bank_code(expense.payment_method)]
    lines = [
        {"account": accounts["5100"], "debit": expense.amount, "description": expense.description},
        {"account": cash_or_bank, "credit": expense.amount, "description": expense.description},
    ]
    entry = create_journal_entry(
        company=expense.company, lines=lines, description=expense.description or "Expense",
        source=JournalEntry.Source.EXPENSE, user=expense.created_by,
    )
    expense.journal_entry = entry
    expense.save(update_fields=["journal_entry"])
    return entry


def close_accounting_period(*, company, user=None) -> JournalEntry | None:
    """Zeroes out every Income/Expense account into Retained Earnings.

    Deliberately period-less rather than tracking fiscal periods: a prior
    close already zeroed out whatever activity came before it (its own
    zeroing lines landed on these same accounts), so summing all-time
    activity on an Income/Expense account is exactly "activity since the
    last close" whether that was yesterday or never. Returns None if there's
    nothing to close (e.g. called twice in a row with no activity between).
    """
    accounts = Account.objects.filter(
        company=company, is_active=True,
        account_type__in=[Account.AccountType.INCOME, Account.AccountType.EXPENSE],
    )
    sums = (
        JournalEntryLine.objects.filter(company=company, account__in=accounts)
        .values("account").annotate(debit_sum=Sum("debit"), credit_sum=Sum("credit"))
    )
    sums_by_account = {row["account"]: (row["debit_sum"] or Decimal("0"), row["credit_sum"] or Decimal("0")) for row in sums}

    lines = []
    net_income = Decimal("0")
    for account in accounts:
        debit_sum, credit_sum = sums_by_account.get(account.id, (Decimal("0"), Decimal("0")))
        balance = debit_sum - credit_sum if account.is_debit_normal else credit_sum - debit_sum
        if not balance:
            continue
        if account.account_type == Account.AccountType.INCOME:
            lines.append({"account": account, "debit": balance, "description": "Period close"})
            net_income += balance
        else:
            lines.append({"account": account, "credit": balance, "description": "Period close"})
            net_income -= balance

    if not lines:
        return None

    retained_earnings = Account.objects.get(company=company, code="3100")
    if net_income > 0:
        lines.append({"account": retained_earnings, "credit": net_income, "description": "Net income to retained earnings"})
    elif net_income < 0:
        lines.append({"account": retained_earnings, "debit": -net_income, "description": "Net loss to retained earnings"})

    return create_journal_entry(
        company=company, lines=lines, description="Period-end close",
        source=JournalEntry.Source.CLOSING, user=user,
    )
