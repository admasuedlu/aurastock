class ExpenseCategory {
  ExpenseCategory({required this.id, required this.name});
  factory ExpenseCategory.fromJson(Map<String, dynamic> json) =>
      ExpenseCategory(id: json['id'] as String, name: json['name'] as String);
  final String id;
  final String name;
}

class Expense {
  Expense({
    required this.id,
    required this.categoryName,
    required this.amount,
    required this.expenseDate,
    required this.description,
    required this.paymentMethod,
  });

  factory Expense.fromJson(Map<String, dynamic> json) {
    return Expense(
      id: json['id'] as String,
      categoryName: json['category_name'] as String? ?? 'Uncategorized',
      amount: double.tryParse(json['amount'].toString()) ?? 0,
      expenseDate: json['expense_date'] as String,
      description: json['description'] as String? ?? '',
      paymentMethod: json['payment_method'] as String,
    );
  }

  final String id;
  final String categoryName;
  final double amount;
  final String expenseDate;
  final String description;
  final String paymentMethod;
}

class TrialBalanceRow {
  TrialBalanceRow({
    required this.accountCode,
    required this.accountName,
    required this.accountType,
    required this.debit,
    required this.credit,
    required this.balance,
  });

  factory TrialBalanceRow.fromJson(Map<String, dynamic> json) {
    return TrialBalanceRow(
      accountCode: json['account_code'] as String,
      accountName: json['account_name'] as String,
      accountType: json['account_type'] as String,
      debit: double.tryParse(json['debit'].toString()) ?? 0,
      credit: double.tryParse(json['credit'].toString()) ?? 0,
      balance: double.tryParse(json['balance'].toString()) ?? 0,
    );
  }

  final String accountCode;
  final String accountName;
  final String accountType;
  final double debit;
  final double credit;
  final double balance;
}

class TrialBalance {
  TrialBalance({required this.rows, required this.totalDebit, required this.totalCredit, required this.isBalanced});

  factory TrialBalance.fromJson(Map<String, dynamic> json) {
    return TrialBalance(
      rows: (json['rows'] as List).map((e) => TrialBalanceRow.fromJson(e as Map<String, dynamic>)).toList(),
      totalDebit: double.tryParse(json['total_debit'].toString()) ?? 0,
      totalCredit: double.tryParse(json['total_credit'].toString()) ?? 0,
      isBalanced: json['is_balanced'] as bool,
    );
  }

  final List<TrialBalanceRow> rows;
  final double totalDebit;
  final double totalCredit;
  final bool isBalanced;
}

class LedgerAmountRow {
  LedgerAmountRow({required this.accountCode, required this.accountName, required this.amount});

  factory LedgerAmountRow.fromJson(Map<String, dynamic> json) {
    return LedgerAmountRow(
      accountCode: json['account_code'] as String,
      accountName: json['account_name'] as String,
      amount: double.tryParse((json['amount'] ?? json['balance']).toString()) ?? 0,
    );
  }

  final String accountCode;
  final String accountName;
  final double amount;
}

class ProfitAndLoss {
  ProfitAndLoss({
    required this.income,
    required this.expenses,
    required this.totalIncome,
    required this.totalExpense,
    required this.netIncome,
  });

  factory ProfitAndLoss.fromJson(Map<String, dynamic> json) {
    return ProfitAndLoss(
      income: (json['income'] as List).map((e) => LedgerAmountRow.fromJson(e as Map<String, dynamic>)).toList(),
      expenses: (json['expenses'] as List).map((e) => LedgerAmountRow.fromJson(e as Map<String, dynamic>)).toList(),
      totalIncome: double.tryParse(json['total_income'].toString()) ?? 0,
      totalExpense: double.tryParse(json['total_expense'].toString()) ?? 0,
      netIncome: double.tryParse(json['net_income'].toString()) ?? 0,
    );
  }

  final List<LedgerAmountRow> income;
  final List<LedgerAmountRow> expenses;
  final double totalIncome;
  final double totalExpense;
  final double netIncome;
}

class BalanceSheet {
  BalanceSheet({
    required this.assets,
    required this.liabilities,
    required this.equity,
    required this.totalAssets,
    required this.totalLiabilities,
    required this.totalEquity,
  });

  factory BalanceSheet.fromJson(Map<String, dynamic> json) {
    return BalanceSheet(
      assets: (json['assets'] as List).map((e) => LedgerAmountRow.fromJson(e as Map<String, dynamic>)).toList(),
      liabilities: (json['liabilities'] as List).map((e) => LedgerAmountRow.fromJson(e as Map<String, dynamic>)).toList(),
      equity: (json['equity'] as List).map((e) => LedgerAmountRow.fromJson(e as Map<String, dynamic>)).toList(),
      totalAssets: double.tryParse(json['total_assets'].toString()) ?? 0,
      totalLiabilities: double.tryParse(json['total_liabilities'].toString()) ?? 0,
      totalEquity: double.tryParse(json['total_equity'].toString()) ?? 0,
    );
  }

  final List<LedgerAmountRow> assets;
  final List<LedgerAmountRow> liabilities;
  final List<LedgerAmountRow> equity;
  final double totalAssets;
  final double totalLiabilities;
  final double totalEquity;

  bool get isBalanced => (totalAssets - (totalLiabilities + totalEquity)).abs() < 0.01;
}

class ClosePeriodResult {
  ClosePeriodResult({required this.closed, required this.detail});

  factory ClosePeriodResult.fromJson(Map<String, dynamic> json) {
    final entry = json['journal_entry'] as Map<String, dynamic>?;
    return ClosePeriodResult(
      closed: json['closed'] as bool,
      detail: entry != null
          ? 'Closed as ${entry['number']}.'
          : (json['detail'] as String? ?? 'Nothing to close.'),
    );
  }

  final bool closed;
  final String detail;
}
