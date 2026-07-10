import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/accounting_repository.dart';
import '../domain/accounting_models.dart';

final accountingRepositoryProvider = Provider<AccountingRepository>((ref) {
  return AccountingRepository(ref.watch(apiClientProvider).dio);
});

final expenseCategoryListProvider = FutureProvider.autoDispose<List<ExpenseCategory>>((ref) {
  return ref.watch(accountingRepositoryProvider).fetchExpenseCategories();
});

final expenseListProvider = FutureProvider.autoDispose<List<Expense>>((ref) {
  return ref.watch(accountingRepositoryProvider).fetchExpenses();
});

final trialBalanceProvider = FutureProvider.autoDispose<TrialBalance>((ref) {
  return ref.watch(accountingRepositoryProvider).fetchTrialBalance();
});

final profitAndLossProvider = FutureProvider.autoDispose<ProfitAndLoss>((ref) {
  return ref.watch(accountingRepositoryProvider).fetchProfitAndLoss();
});

final balanceSheetProvider = FutureProvider.autoDispose<BalanceSheet>((ref) {
  return ref.watch(accountingRepositoryProvider).fetchBalanceSheet();
});
