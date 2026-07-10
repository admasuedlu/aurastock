import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../providers/reports_providers.dart';

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 5,
      child: Scaffold(
        appBar: AppBar(
          title: Text(AppLocalizations.of(context).reports),
          bottom: const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'Top Products'),
              Tab(text: 'ABC Analysis'),
              Tab(text: 'Purchases'),
              Tab(text: 'Inventory Valuation'),
              Tab(text: 'Dead Stock'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [_TopProductsTab(), _AbcTab(), _PurchasesTab(), _ValuationTab(), _DeadStockTab()],
        ),
      ),
    );
  }
}

class _TopProductsTab extends ConsumerWidget {
  const _TopProductsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final topProductsAsync = ref.watch(topProductsProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return topProductsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (rows) {
        if (rows.isEmpty) return Center(child: Text(l10n.noData));
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: rows.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final row = rows[index];
            return Card(
              child: ListTile(
                leading: CircleAvatar(child: Text('${index + 1}')),
                title: Text(row.productName),
                subtitle: Text('${row.productSku} · ${row.quantitySold.toStringAsFixed(0)} sold'),
                trailing: Text(currency.format(row.revenue), style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
            );
          },
        );
      },
    );
  }
}

Color _abcColor(String abcClass) {
  switch (abcClass) {
    case 'A':
      return Colors.green;
    case 'B':
      return Colors.orange;
    default:
      return Colors.blueGrey;
  }
}

class _AbcTab extends ConsumerWidget {
  const _AbcTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final abcAsync = ref.watch(abcAnalysisProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return abcAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (abc) {
        if (abc.rows.isEmpty) {
          return Center(child: Text(l10n.noData));
        }
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Products ranked by revenue share over the last year. Class A is '
              'the vital few (top 80% of revenue), C the trivial many.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                for (final band in abc.summary)
                  Expanded(
                    child: Card(
                      color: _abcColor(band.abcClass).withValues(alpha: 0.12),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          children: [
                            Text(band.abcClass,
                                style: TextStyle(
                                    color: _abcColor(band.abcClass),
                                    fontWeight: FontWeight.bold,
                                    fontSize: 20)),
                            const SizedBox(height: 4),
                            Text('${band.productCount} item${band.productCount == 1 ? '' : 's'}'),
                            Text('${band.revenuePct.toStringAsFixed(0)}%',
                                style: const TextStyle(fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            for (final row in abc.rows)
              Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: _abcColor(row.abcClass).withValues(alpha: 0.15),
                    child: Text(row.abcClass, style: TextStyle(color: _abcColor(row.abcClass), fontWeight: FontWeight.bold)),
                  ),
                  title: Text(row.productName),
                  subtitle: Text(
                    '${row.productSku} · ${row.quantitySold.toStringAsFixed(0)} sold · '
                    'cumulative ${row.cumulativePct.toStringAsFixed(1)}%',
                  ),
                  trailing: Text(currency.format(row.revenue), style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _PurchasesTab extends ConsumerWidget {
  const _PurchasesTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final purchasesAsync = ref.watch(purchaseSummaryProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
    final dateFormat = DateFormat('MMM d');

    return purchasesAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (summary) {
        final receiptDays = summary.series.where((p) => p.total > 0).toList().reversed.toList();
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: ListTile(
                title: const Text('Received (last 30 days)', style: TextStyle(fontWeight: FontWeight.bold)),
                subtitle: const Text('Goods receipts valued at cost'),
                trailing: Text(
                  currency.format(summary.periodTotal),
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ),
            Row(
              children: [
                Expanded(
                  child: Card(
                    child: ListTile(
                      title: const Text('Today'),
                      trailing: Text(currency.format(summary.todayTotal)),
                    ),
                  ),
                ),
                Expanded(
                  child: Card(
                    child: ListTile(
                      title: const Text('This month'),
                      trailing: Text(currency.format(summary.monthTotal)),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (receiptDays.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 24),
                child: Center(child: Text('No goods received in this window.')),
              )
            else
              for (final point in receiptDays)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.local_shipping_outlined),
                    title: Text(dateFormat.format(point.date)),
                    trailing: Text(currency.format(point.total)),
                  ),
                ),
          ],
        );
      },
    );
  }
}

class _ValuationTab extends ConsumerWidget {
  const _ValuationTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final valuationAsync = ref.watch(inventoryValuationProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return valuationAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (valuation) {
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: ListTile(
                title: const Text('Total Inventory Value', style: TextStyle(fontWeight: FontWeight.bold)),
                trailing: Text(
                  currency.format(valuation.totalValue),
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ),
            const SizedBox(height: 12),
            if (valuation.rows.isEmpty)
              Padding(padding: const EdgeInsets.only(top: 24), child: Text(l10n.noData))
            else
              for (final row in valuation.rows)
                Card(
                  child: ListTile(
                    title: Text(row.productName),
                    subtitle: Text('${row.warehouseName} · ${row.quantityOnHand.toStringAsFixed(0)} on hand'),
                    trailing: Text(currency.format(row.value)),
                  ),
                ),
          ],
        );
      },
    );
  }
}

class _DeadStockTab extends ConsumerWidget {
  const _DeadStockTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final deadStockAsync = ref.watch(deadStockProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return deadStockAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (rows) {
        if (rows.isEmpty) {
          return Center(child: Text('Nothing idle — everything has sold recently.'));
        }
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: rows.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final row = rows[index];
            return Card(
              child: ListTile(
                leading: const Icon(Icons.inventory_outlined, color: Colors.grey),
                title: Text(row.productName),
                subtitle: Text(
                  '${row.warehouseName} · ${row.quantityOnHand.toStringAsFixed(0)} on hand · '
                  '${row.lastSoldAt == null ? "never sold" : "last sold ${row.lastSoldAt!.substring(0, 10)}"}',
                ),
                trailing: Text(currency.format(row.value)),
              ),
            );
          },
        );
      },
    );
  }
}
