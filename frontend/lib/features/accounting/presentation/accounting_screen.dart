import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../domain/accounting_models.dart';
import '../providers/accounting_providers.dart';
import 'expense_form_sheet.dart';

class AccountingScreen extends ConsumerStatefulWidget {
  const AccountingScreen({super.key});

  @override
  ConsumerState<AccountingScreen> createState() => _AccountingScreenState();
}

class _AccountingScreenState extends ConsumerState<AccountingScreen> {
  int _tabIndex = 0;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Accounting'),
          bottom: TabBar(
            isScrollable: true,
            onTap: (i) => setState(() => _tabIndex = i),
            tabs: const [
              Tab(text: 'Expenses'),
              Tab(text: 'Trial Balance'),
              Tab(text: 'Profit & Loss'),
              Tab(text: 'Balance Sheet'),
            ],
          ),
        ),
        floatingActionButton: _tabIndex == 0
            ? FloatingActionButton.extended(
                onPressed: () => showExpenseFormSheet(context),
                icon: const Icon(Icons.add),
                label: const Text('Add Expense'),
              )
            : null,
        body: const TabBarView(
          children: [
            _ExpensesTab(),
            _TrialBalanceTab(),
            _ProfitAndLossTab(),
            _BalanceSheetTab(),
          ],
        ),
      ),
    );
  }
}

class _ExpensesTab extends ConsumerWidget {
  const _ExpensesTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final expensesAsync = ref.watch(expenseListProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return expensesAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (expenses) {
        if (expenses.isEmpty) return Center(child: Text(l10n.noData));
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: expenses.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final expense = expenses[index];
            return Card(
              child: ListTile(
                title: Text(expense.description),
                subtitle: Text('${expense.categoryName} · ${expense.paymentMethod} · ${expense.expenseDate}'),
                trailing: Text(currency.format(expense.amount), style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
            );
          },
        );
      },
    );
  }
}

class _TrialBalanceTab extends ConsumerWidget {
  const _TrialBalanceTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final trialBalanceAsync = ref.watch(trialBalanceProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return trialBalanceAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (trialBalance) {
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              color: trialBalance.isBalanced
                  ? Colors.green.withValues(alpha: 0.1)
                  : Colors.red.withValues(alpha: 0.1),
              child: ListTile(
                leading: Icon(
                  trialBalance.isBalanced ? Icons.check_circle_outline : Icons.error_outline,
                  color: trialBalance.isBalanced ? Colors.green : Colors.red,
                ),
                title: Text(trialBalance.isBalanced ? 'Books are balanced' : 'Books are NOT balanced'),
                subtitle: Text(
                  'Total debit ${currency.format(trialBalance.totalDebit)} · '
                  'Total credit ${currency.format(trialBalance.totalCredit)}',
                ),
              ),
            ),
            const SizedBox(height: 12),
            for (final row in trialBalance.rows.where((r) => r.debit != 0 || r.credit != 0))
              Card(
                child: ListTile(
                  title: Text('${row.accountCode} ${row.accountName}'),
                  subtitle: Text(row.accountType),
                  trailing: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('Dr ${currency.format(row.debit)}'),
                      Text('Cr ${currency.format(row.credit)}'),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _ProfitAndLossTab extends ConsumerWidget {
  const _ProfitAndLossTab();

  Widget _rows(BuildContext context, List<LedgerAmountRow> rows, NumberFormat currency) {
    return Column(
      children: rows
          .map((row) => ListTile(
                title: Text('${row.accountCode} ${row.accountName}'),
                trailing: Text(currency.format(row.amount)),
              ))
          .toList(),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final pnlAsync = ref.watch(profitAndLossProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return pnlAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (pnl) {
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Income', style: Theme.of(context).textTheme.titleMedium),
            Card(child: _rows(context, pnl.income, currency)),
            const SizedBox(height: 16),
            Text('Expenses', style: Theme.of(context).textTheme.titleMedium),
            Card(child: _rows(context, pnl.expenses, currency)),
            const SizedBox(height: 16),
            Card(
              color: pnl.netIncome >= 0
                  ? Colors.green.withValues(alpha: 0.1)
                  : Colors.red.withValues(alpha: 0.1),
              child: ListTile(
                title: const Text('Net Income', style: TextStyle(fontWeight: FontWeight.bold)),
                trailing: Text(
                  currency.format(pnl.netIncome),
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _BalanceSheetTab extends ConsumerStatefulWidget {
  const _BalanceSheetTab();

  @override
  ConsumerState<_BalanceSheetTab> createState() => _BalanceSheetTabState();
}

class _BalanceSheetTabState extends ConsumerState<_BalanceSheetTab> {
  bool _closing = false;

  Widget _section(BuildContext context, String title, List<LedgerAmountRow> rows, double total, NumberFormat currency) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        Card(
          child: Column(
            children: [
              ...rows.map((row) => ListTile(
                    title: Text('${row.accountCode} ${row.accountName}'),
                    trailing: Text(currency.format(row.amount)),
                  )),
              ListTile(
                title: const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)),
                trailing: Text(currency.format(total), style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Future<void> _closePeriod() async {
    setState(() => _closing = true);
    try {
      final result = await ref.read(accountingRepositoryProvider).closePeriod();
      ref.invalidate(balanceSheetProvider);
      ref.invalidate(trialBalanceProvider);
      ref.invalidate(profitAndLossProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(result.detail)));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _closing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final balanceSheetAsync = ref.watch(balanceSheetProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return balanceSheetAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (sheet) {
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _section(context, 'Assets', sheet.assets, sheet.totalAssets, currency),
            _section(context, 'Liabilities', sheet.liabilities, sheet.totalLiabilities, currency),
            _section(context, 'Equity', sheet.equity, sheet.totalEquity, currency),
            Card(
              color: sheet.isBalanced
                  ? Colors.green.withValues(alpha: 0.1)
                  : Colors.orange.withValues(alpha: 0.1),
              child: ListTile(
                leading: Icon(
                  sheet.isBalanced ? Icons.check_circle_outline : Icons.info_outline,
                  color: sheet.isBalanced ? Colors.green : Colors.orange,
                ),
                title: Text(sheet.isBalanced ? 'Assets = Liabilities + Equity' : 'Assets ≠ Liabilities + Equity'),
                subtitle: Text(
                  sheet.isBalanced
                      ? 'Books are closed through today.'
                      : 'Current-period net income is still sitting in Income/Expense '
                        'accounts. Close the period to roll it into Retained Earnings.',
                ),
              ),
            ),
            if (!sheet.isBalanced) ...[
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _closing ? null : _closePeriod,
                icon: _closing
                    ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.lock_clock_outlined),
                label: const Text('Close Period'),
              ),
            ],
          ],
        );
      },
    );
  }
}
