from rest_framework.routers import DefaultRouter

from django.urls import path

from .reports import BalanceSheetView, ProfitAndLossView, TrialBalanceView
from .views import (
    AccountViewSet,
    ClosePeriodView,
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    JournalEntryViewSet,
)

router = DefaultRouter()
router.register("accounting/accounts", AccountViewSet, basename="account")
router.register("accounting/journal-entries", JournalEntryViewSet, basename="journal-entry")
router.register("accounting/expense-categories", ExpenseCategoryViewSet, basename="expense-category")
router.register("accounting/expenses", ExpenseViewSet, basename="expense")

urlpatterns = [
    path("accounting/reports/trial-balance/", TrialBalanceView.as_view(), name="trial-balance"),
    path("accounting/reports/profit-and-loss/", ProfitAndLossView.as_view(), name="profit-and-loss"),
    path("accounting/reports/balance-sheet/", BalanceSheetView.as_view(), name="balance-sheet"),
    path("accounting/close-period/", ClosePeriodView.as_view(), name="close-period"),
] + router.urls
