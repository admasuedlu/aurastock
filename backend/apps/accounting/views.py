from rest_framework import mixins, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.viewsets import CompanyScopedViewSet

from . import services
from .models import Account, Expense, ExpenseCategory, JournalEntry
from .serializers import (
    AccountSerializer,
    ExpenseCategorySerializer,
    ExpenseSerializer,
    JournalEntrySerializer,
)


class AccountViewSet(CompanyScopedViewSet):
    queryset = Account.objects.select_related("parent").all()
    serializer_class = AccountSerializer
    permission_module = "accounting"
    filterset_fields = ["account_type", "is_active"]
    search_fields = ["code", "name"]


class JournalEntryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = JournalEntry.objects.prefetch_related("lines", "lines__account").all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["source"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        return qs if user.is_superuser else qs.filter(company_id=user.company_id)


class ExpenseCategoryViewSet(CompanyScopedViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_module = "accounting"
    search_fields = ["name"]


class ExpenseViewSet(CompanyScopedViewSet):
    queryset = Expense.objects.select_related("category", "journal_entry").all()
    serializer_class = ExpenseSerializer
    permission_module = "accounting"
    filterset_fields = ["category", "payment_method"]

    def perform_create(self, serializer):
        expense = serializer.save(company=self.request.user.company, created_by=self.request.user)
        services.record_expense(expense)


class ClosePeriodView(APIView):
    """Zeroes out Income/Expense accounts into Retained Earnings so the
    balance sheet actually balances (Assets = Liabilities + Equity) going
    forward. Simulates what a real close-the-books action would be -- there's
    no fiscal-period model, so this always closes all activity since the
    last close (see services.close_accounting_period)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        entry = services.close_accounting_period(company=request.user.company, user=request.user)
        if entry is None:
            return Response({"closed": False, "detail": "Nothing to close -- no income or expense activity since the last close."})
        return Response({"closed": True, "journal_entry": JournalEntrySerializer(entry).data})
