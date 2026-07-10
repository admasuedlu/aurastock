from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Account, JournalEntryLine


def _parse_date(value, default):
    if not value:
        return default
    return date.fromisoformat(value)


def _account_balances(company, account_types=None, start=None, end=None):
    """Returns {account: (debit_sum, credit_sum)} for every active account
    of the given types with journal activity in [start, end]."""
    accounts = Account.objects.filter(company=company, is_active=True)
    if account_types:
        accounts = accounts.filter(account_type__in=account_types)

    lines = JournalEntryLine.objects.filter(company=company, account__in=accounts)
    if start:
        lines = lines.filter(journal_entry__entry_date__gte=start)
    if end:
        lines = lines.filter(journal_entry__entry_date__lte=end)

    sums = lines.values("account").annotate(debit_sum=Sum("debit"), credit_sum=Sum("credit"))
    sums_by_account = {row["account"]: (row["debit_sum"] or Decimal("0"), row["credit_sum"] or Decimal("0")) for row in sums}

    return {account: sums_by_account.get(account.id, (Decimal("0"), Decimal("0"))) for account in accounts}


class TrialBalanceView(APIView):
    """As-of trial balance across every account. Debit and credit totals
    must match by construction (every journal entry is balanced at
    creation) -- this endpoint is also a live integrity check of that."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        as_of = _parse_date(request.query_params.get("as_of"), date.today())
        balances = _account_balances(request.user.company, end=as_of)

        rows = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for account, (debit_sum, credit_sum) in sorted(balances.items(), key=lambda kv: kv[0].code):
            balance = debit_sum - credit_sum if account.is_debit_normal else credit_sum - debit_sum
            rows.append({
                "account_code": account.code, "account_name": account.name, "account_type": account.account_type,
                "debit": debit_sum, "credit": credit_sum, "balance": balance,
            })
            total_debit += debit_sum
            total_credit += credit_sum

        return Response({
            "as_of": as_of.isoformat(), "rows": rows,
            "total_debit": total_debit, "total_credit": total_credit,
            "is_balanced": total_debit == total_credit,
        })


class ProfitAndLossView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = _parse_date(request.query_params.get("start"), date(date.today().year, 1, 1))
        end = _parse_date(request.query_params.get("end"), date.today())

        income_balances = _account_balances(
            request.user.company, account_types=[Account.AccountType.INCOME], start=start, end=end,
        )
        expense_balances = _account_balances(
            request.user.company, account_types=[Account.AccountType.EXPENSE], start=start, end=end,
        )

        def _rows(balances):
            result = []
            for account, (debit_sum, credit_sum) in sorted(balances.items(), key=lambda kv: kv[0].code):
                amount = debit_sum - credit_sum if account.is_debit_normal else credit_sum - debit_sum
                result.append({"account_code": account.code, "account_name": account.name, "amount": amount})
            return result

        income_rows = _rows(income_balances)
        expense_rows = _rows(expense_balances)
        total_income = sum((row["amount"] for row in income_rows), Decimal("0"))
        total_expense = sum((row["amount"] for row in expense_rows), Decimal("0"))

        return Response({
            "start": start.isoformat(), "end": end.isoformat(),
            "income": income_rows, "expenses": expense_rows,
            "total_income": total_income, "total_expense": total_expense,
            "net_income": total_income - total_expense,
        })


class BalanceSheetView(APIView):
    """Assets/Liabilities/Equity as of a date. Note: this does not run a
    period-end close, so current-period net income sits implicitly in the
    Income/Expense accounts rather than being rolled into Retained Earnings
    -- assets will not equal liabilities + equity until a closing entry
    moves that net income across. That closing step isn't implemented yet."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        as_of = _parse_date(request.query_params.get("as_of"), date.today())
        company = request.user.company

        def _rows(account_types):
            balances = _account_balances(company, account_types=account_types, end=as_of)
            result = []
            for account, (debit_sum, credit_sum) in sorted(balances.items(), key=lambda kv: kv[0].code):
                balance = debit_sum - credit_sum if account.is_debit_normal else credit_sum - debit_sum
                result.append({"account_code": account.code, "account_name": account.name, "balance": balance})
            return result

        asset_rows = _rows([Account.AccountType.ASSET])
        liability_rows = _rows([Account.AccountType.LIABILITY])
        equity_rows = _rows([Account.AccountType.EQUITY])

        return Response({
            "as_of": as_of.isoformat(),
            "assets": asset_rows, "liabilities": liability_rows, "equity": equity_rows,
            "total_assets": sum((r["balance"] for r in asset_rows), Decimal("0")),
            "total_liabilities": sum((r["balance"] for r in liability_rows), Decimal("0")),
            "total_equity": sum((r["balance"] for r in equity_rows), Decimal("0")),
        })
