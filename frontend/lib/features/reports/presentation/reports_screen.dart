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
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text(AppLocalizations.of(context).reports),
          bottom: const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'Top Products'),
              Tab(text: 'Inventory Valuation'),
              Tab(text: 'Dead Stock'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [_TopProductsTab(), _ValuationTab(), _DeadStockTab()],
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
