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
    isScrollControlled: true,
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
  // One quantity field per still-outstanding line, pre-filled with the full
  // outstanding amount so "just create the invoice" bills the whole remainder.
  final Map<String, TextEditingController> _qtyControllers = {};

  @override
  void initState() {
    super.initState();
    for (final line in widget.order.outstandingLines) {
      _qtyControllers[line.id] = TextEditingController(text: _trim(line.quantityOutstanding));
    }
  }

  @override
  void dispose() {
    for (final controller in _qtyControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  /// Drops trailing decimal zeros so "6.000" shows as "6", "2.500" as "2.5".
  String _trim(double value) => value.toStringAsFixed(3).replaceFirst(RegExp(r'\.?0+$'), '');

  Future<void> _convert() async {
    if (_warehouseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a warehouse to invoice from.')),
      );
      return;
    }
    final items = <Map<String, dynamic>>[];
    for (final line in widget.order.outstandingLines) {
      final qty = double.tryParse(_qtyControllers[line.id]!.text.trim()) ?? 0;
      if (qty <= 0) continue;
      if (qty > line.quantityOutstanding) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(
            '${line.productName}: only ${_trim(line.quantityOutstanding)} left to invoice.',
          )),
        );
        return;
      }
      items.add({'sales_order_item': line.id, 'quantity': qty});
    }
    if (items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a quantity for at least one line.')),
      );
      return;
    }

    setState(() => _busy = true);
    try {
      await ref.read(salesRepositoryProvider).convertSalesOrderToInvoice(
            widget.order.id, warehouseId: _warehouseId!, items: items,
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
    final warehousesAsync = ref.watch(warehouseListProvider);

    return Padding(
      padding: EdgeInsets.only(
        left: 20, right: 20, top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: SingleChildScrollView(
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
                const Text('Order total'),
                Text(currency.format(order.total), style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 16),
            if (_busy)
              const Center(child: CircularProgressIndicator())
            else if (!order.canInvoice)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(order.status == 'cancelled'
                    ? 'This order is cancelled.'
                    : 'This order is fully invoiced.'),
              )
            else ...[
              warehousesAsync.when(
                loading: () => const LinearProgressIndicator(),
                error: (_, _) => Text(l10n.errorGeneric),
                data: (warehouses) => DropdownButtonFormField<String>(
                  initialValue: _warehouseId,
                  decoration: InputDecoration(labelText: l10n.warehouse),
                  items: warehouses
                      .map((w) => DropdownMenuItem(value: w.id, child: Text(w.name)))
                      .toList(),
                  onChanged: (v) => setState(() => _warehouseId = v),
                ),
              ),
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerLeft,
                child: Text('Quantities to invoice', style: Theme.of(context).textTheme.labelLarge),
              ),
              const SizedBox(height: 8),
              for (final line in order.outstandingLines)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(line.productName),
                            Text(
                              '${_trim(line.quantityOutstanding)} of ${_trim(line.quantity)} left',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      SizedBox(
                        width: 90,
                        child: TextField(
                          controller: _qtyControllers[line.id],
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          textAlign: TextAlign.right,
                          decoration: const InputDecoration(labelText: 'Qty', isDense: true),
                        ),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 8),
              Text(
                'Creates a draft invoice for the entered quantities — leave them as-is to '
                'invoice everything outstanding. Confirming that invoice deducts stock.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _convert,
                icon: const Icon(Icons.receipt_long),
                label: const Text('Create Invoice'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
