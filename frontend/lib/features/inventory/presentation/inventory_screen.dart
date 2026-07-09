import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../providers/inventory_providers.dart';
import 'stock_action_sheet.dart';

class InventoryScreen extends ConsumerWidget {
  const InventoryScreen({super.key});

  void _openActionMenu(BuildContext context, AppLocalizations l10n) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.arrow_downward),
              title: Text(l10n.stockIn),
              onTap: () {
                Navigator.pop(context);
                showStockActionSheet(context, StockActionType.stockIn);
              },
            ),
            ListTile(
              leading: const Icon(Icons.arrow_upward),
              title: Text(l10n.stockOut),
              onTap: () {
                Navigator.pop(context);
                showStockActionSheet(context, StockActionType.stockOut);
              },
            ),
            ListTile(
              leading: const Icon(Icons.compare_arrows),
              title: Text(l10n.stockTransfer),
              onTap: () {
                Navigator.pop(context);
                showStockActionSheet(context, StockActionType.transfer);
              },
            ),
            ListTile(
              leading: const Icon(Icons.tune),
              title: Text(l10n.stockAdjustment),
              onTap: () {
                Navigator.pop(context);
                showStockActionSheet(context, StockActionType.adjustment);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _createWarehouse(BuildContext context, WidgetRef ref) async {
    final nameController = TextEditingController();
    final codeController = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New warehouse'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Name')),
            TextField(controller: codeController, decoration: const InputDecoration(labelText: 'Code')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Create')),
        ],
      ),
    );
    if (result == true && context.mounted) {
      try {
        await ref.read(inventoryRepositoryProvider).createWarehouse(
              name: nameController.text.trim(),
              code: codeController.text.trim(),
            );
        ref.invalidate(warehouseListProvider);
      } on DioException catch (_) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not create warehouse.')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final stockAsync = ref.watch(stockItemListProvider);
    final movementsAsync = ref.watch(movementListProvider);

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.inventory),
          actions: [
            IconButton(
              icon: const Icon(Icons.add_business_outlined),
              tooltip: 'New warehouse',
              onPressed: () => _createWarehouse(context, ref),
            ),
          ],
          bottom: const TabBar(tabs: [Tab(text: 'Stock Levels'), Tab(text: 'History')]),
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () => _openActionMenu(context, l10n),
          child: const Icon(Icons.add),
        ),
        body: TabBarView(
          children: [
            stockAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text(l10n.errorGeneric)),
              data: (items) {
                if (items.isEmpty) return Center(child: Text(l10n.noData));
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return Card(
                      child: ListTile(
                        leading: Icon(
                          item.isLowStock ? Icons.warning_amber_rounded : Icons.check_circle_outline,
                          color: item.isLowStock ? Colors.orange : Colors.green,
                        ),
                        title: Text(item.productName),
                        subtitle: Text('${item.warehouseName} · ${item.productSku}'),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text('${item.quantityOnHand.toStringAsFixed(0)}', style: const TextStyle(fontWeight: FontWeight.bold)),
                            Text(l10n.onHandStock, style: Theme.of(context).textTheme.bodySmall),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
            movementsAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text(l10n.errorGeneric)),
              data: (movements) {
                if (movements.isEmpty) return Center(child: Text(l10n.noData));
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: movements.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final movement = movements[index];
                    return Card(
                      child: ListTile(
                        leading: Icon(_iconFor(movement.movementType)),
                        title: Text(movement.productName),
                        subtitle: Text('${movement.warehouseName} · ${movement.movementType}'),
                        trailing: Text(movement.quantity.toStringAsFixed(0)),
                      ),
                    );
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  IconData _iconFor(String movementType) {
    switch (movementType) {
      case 'stock_in':
        return Icons.arrow_downward;
      case 'stock_out':
        return Icons.arrow_upward;
      case 'transfer_in':
      case 'transfer_out':
        return Icons.compare_arrows;
      default:
        return Icons.tune;
    }
  }
}
