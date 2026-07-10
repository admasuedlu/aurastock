from rest_framework import mixins, permissions, viewsets

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
    search_fields = ["name"]


class ExpenseViewSet(CompanyScopedViewSet):
    queryset = Expense.objects.select_related("category", "journal_entry").all()
    serializer_class = ExpenseSerializer
    filterset_fields = ["category", "payment_method"]

    def perform_create(self, serializer):
        expense = serializer.save(company=self.request.user.company, created_by=self.request.user)
        services.record_expense(expense)
