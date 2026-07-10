import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../inventory/providers/inventory_providers.dart';
import '../domain/sales_models.dart';
import '../providers/sales_providers.dart';

Future<void> showSalesOrderActionsSheet(BuildContext context, WidgetRef ref, SalesOrder order) {
  return showModalBottomSheet(
    context: context,
    builder: (context) => _SalesOrderActionsSheet(order: order),
  );
}

class _SalesOrderActionsSheet extends ConsumerStatefulWidget {
  const _SalesOrderActionsSheet({required this.order});
  final SalesOrder order;

  @override
  ConsumerState<_SalesOrderActionsSheet> createState() => _SalesOrderActionsSheetState();
}

class _SalesOrderActionsSheetState extends ConsumerState<_SalesOrderActionsSheet> {
  String? _warehouseId;
  bool _busy = false;

  Future<void> _convert() async {
    if (_warehouseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a warehouse to invoice from.')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(salesRepositoryProvider).convertSalesOrderToInvoice(
            widget.order.id, warehouseId: _warehouseId!,
          );
      ref.invalidate(salesOrderListProvider);
      ref.invalidate(invoiceListProvider);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Draft invoice created from this order.')),
        );
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
    final order = widget.order;
    // Only a draft order can be turned into an invoice; conversion moves it to
    // confirmed, and the backend blocks a second invoice regardless.
    final canInvoice = order.status == 'draft';
    final warehousesAsync = ref.watch(warehouseListProvider);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(order.number, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(order.customerName),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total'),
                Text(currency.format(order.total), style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 20),
            if (_busy)
              const Center(child: CircularProgressIndicator())
            else if (canInvoice) ...[
              warehousesAsync.when(
                loading: () => const LinearProgressIndicator(),
                error: (_, __) => Text(l10n.errorGeneric),
                data: (warehouses) => DropdownButtonFormField<String>(
                  initialValue: _warehouseId,
                  decoration: InputDecoration(labelText: l10n.warehouse),
                  items: warehouses
                      .map((w) => DropdownMenuItem(value: w.id, child: Text(w.name)))
                      .toList(),
                  onChanged: (v) => setState(() => _warehouseId = v),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Creates a draft invoice with these line items. Confirming that '
                'invoice will deduct stock from the chosen warehouse.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _convert,
                icon: const Icon(Icons.receipt_long),
                label: const Text('Create Invoice'),
              ),
            ] else
              Text('This order is ${order.status} and has already been invoiced.'),
          ],
        ),
      ),
    );
  }
}
