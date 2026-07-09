import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/providers/auth_controller.dart';
import '../../inventory/providers/inventory_providers.dart';
import '../../products/providers/product_providers.dart';
import 'widgets/kpi_card.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final user = ref.watch(authControllerProvider).valueOrNull;
    final productsAsync = ref.watch(productListProvider);
    final stockAsync = ref.watch(stockItemListProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.dashboard),
        actions: [
          if (user != null)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(child: Text(user.fullName.isEmpty ? user.email : user.fullName)),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(productListProvider);
          ref.invalidate(stockItemListProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          child: stockAsync.when(
            loading: () => const Padding(
              padding: EdgeInsets.only(top: 80),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (err, _) => Padding(
              padding: const EdgeInsets.only(top: 80),
              child: Center(child: Text(l10n.errorGeneric)),
            ),
            data: (stockItems) {
              final inventoryValue = stockItems.fold<double>(0, (sum, item) => sum + item.stockValue);
              final lowStockCount = stockItems.where((item) => item.isLowStock).length;
              final productCount = productsAsync.valueOrNull?.length ?? 0;

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final columns = constraints.maxWidth >= 900 ? 4 : (constraints.maxWidth >= 600 ? 2 : 1);
                      return GridView.count(
                        crossAxisCount: columns,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        mainAxisSpacing: 16,
                        crossAxisSpacing: 16,
                        childAspectRatio: 1.5,
                        children: [
                          KpiCard(
                            label: l10n.inventoryValue,
                            value: currency.format(inventoryValue),
                            icon: Icons.account_balance_wallet_outlined,
                          ),
                          KpiCard(
                            label: l10n.totalProducts,
                            value: '$productCount',
                            icon: Icons.inventory_2_outlined,
                          ),
                          KpiCard(
                            label: l10n.lowStockItems,
                            value: '$lowStockCount',
                            icon: Icons.warning_amber_rounded,
                            color: lowStockCount > 0 ? Colors.orange : null,
                          ),
                          KpiCard(
                            label: l10n.todaySales,
                            value: currency.format(0),
                            icon: Icons.point_of_sale_outlined,
                            color: Theme.of(context).colorScheme.outline,
                          ),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 28),
                  Text(l10n.lowStockItems, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  if (lowStockCount == 0)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 24),
                      child: Text(l10n.noData, style: Theme.of(context).textTheme.bodyMedium),
                    )
                  else
                    Card(
                      child: Column(
                        children: stockItems.where((item) => item.isLowStock).map((item) {
                          return ListTile(
                            leading: const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                            title: Text(item.productName),
                            subtitle: Text('${item.warehouseName} · ${item.productSku}'),
                            trailing: Text('${item.quantityOnHand.toStringAsFixed(0)} / ${item.reorderLevel.toStringAsFixed(0)}'),
                          );
                        }).toList(),
                      ),
                    ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
