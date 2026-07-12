import 'package:dio/dio.dart';

import '../domain/accounting_models.dart';

class AccountingRepository {
  AccountingRepository(this._dio);
  final Dio _dio;

  Future<List<ExpenseCategory>> fetchExpenseCategories() async {
    final response = await _dio.get('/accounting/expense-categories/');
    final results = response.data['results'] as List;
    return results.map((e) => ExpenseCategory.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<ExpenseCategory> createExpenseCategory(String name) async {
    final response = await _dio.post('/accounting/expense-categories/', data: {'name': name});
    return ExpenseCategory.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<Expense>> fetchExpenses() async {
    final response = await _dio.get('/accounting/expenses/');
    final results = response.data['results'] as List;
    return results.map((e) => Expense.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Expense> createExpense({
    String? categoryId,
    required double amount,
    required String description,
    required String paymentMethod,
  }) async {
    final response = await _dio.post('/accounting/expenses/', data: {
      'category': ?categoryId,
      'amount': amount,
      'description': description,
      'payment_method': paymentMethod,
    });
    return Expense.fromJson(response.data as Map<String, dynamic>);
  }

  Future<TrialBalance> fetchTrialBalance() async {
    final response = await _dio.get('/accounting/reports/trial-balance/');
    return TrialBalance.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ProfitAndLoss> fetchProfitAndLoss() async {
    final response = await _dio.get('/accounting/reports/profit-and-loss/');
    return ProfitAndLoss.fromJson(response.data as Map<String, dynamic>);
  }

  Future<BalanceSheet> fetchBalanceSheet() async {
    final response = await _dio.get('/accounting/reports/balance-sheet/');
    return BalanceSheet.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ClosePeriodResult> closePeriod() async {
    final response = await _dio.post('/accounting/close-period/');
    return ClosePeriodResult.fromJson(response.data as Map<String, dynamic>);
  }
}
