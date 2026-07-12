import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../inventory/providers/inventory_providers.dart';
import '../domain/purchasing_models.dart';
import '../providers/purchasing_providers.dart';

Future<void> showReceiveGoodsSheet(BuildContext context, PurchaseOrder order) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => _ReceiveGoodsSheet(order: order),
  );
}

class _ReceiveGoodsSheet extends ConsumerStatefulWidget {
  const _ReceiveGoodsSheet({required this.order});
  final PurchaseOrder order;

  @override
  ConsumerState<_ReceiveGoodsSheet> createState() => _ReceiveGoodsSheetState();
}

class _ReceiveGoodsSheetState extends ConsumerState<_ReceiveGoodsSheet> {
  String? _warehouseId;
  bool _submitting = false;
  late final List<TextEditingController> _qtyControllers;

  List<PurchaseOrderItem> get _outstandingItems =>
      widget.order.items.where((i) => i.quantityOutstanding > 0).toList();

  @override
  void initState() {
    super.initState();
    _qtyControllers = _outstandingItems
        .map((i) => TextEditingController(text: i.quantityOutstanding.toStringAsFixed(0)))
        .toList();
  }

  @override
  void dispose() {
    for (final c in _qtyControllers) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_warehouseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Pick a warehouse.')));
      return;
    }
    final items = <Map<String, dynamic>>[];
    for (int i = 0; i < _outstandingItems.length; i++) {
      final qty = double.tryParse(_qtyControllers[i].text) ?? 0;
      if (qty <= 0) continue;
      final item = _outstandingItems[i];
      items.add({
        'purchase_order_item': item.id,
        'product': item.productId,
        'quantity': qty,
        'unit_cost': item.unitPrice,
      });
    }
    if (items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter at least one quantity to receive.')));
      return;
    }

    setState(() => _submitting = true);
    try {
      await ref.read(purchasingRepositoryProvider).receiveGoods(
            purchaseOrderId: widget.order.id, warehouseId: _warehouseId!, items: items,
          );
      ref.invalidate(purchaseOrderListProvider);
      ref.invalidate(stockItemListProvider);
      ref.invalidate(lowStockItemListProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final warehousesAsync = ref.watch(warehouseListProvider);
    final items = _outstandingItems;

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
            Text('Receive goods — ${widget.order.number}', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 20),
            warehousesAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, _) => const SizedBox.shrink(),
              data: (warehouses) => DropdownButtonFormField<String>(
                initialValue: _warehouseId,
                decoration: InputDecoration(labelText: l10n.warehouse),
                items: warehouses.map((w) => DropdownMenuItem(value: w.id, child: Text(w.name))).toList(),
                onChanged: (v) => setState(() => _warehouseId = v),
              ),
            ),
            const SizedBox(height: 20),
            if (items.isEmpty)
              const Text('Everything on this order has already been received.')
            else
              for (int i = 0; i < items.length; i++)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: Text('${items[i].productName}\n(outstanding: ${items[i].quantityOutstanding.toStringAsFixed(0)})'),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          controller: _qtyControllers[i],
                          decoration: const InputDecoration(labelText: 'Receive qty'),
                          keyboardType: TextInputType.number,
                        ),
                      ),
                    ],
                  ),
                ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: (_submitting || items.isEmpty) ? null : _submit,
              child: _submitting
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Receive'),
            ),
          ],
        ),
      ),
    );
  }
}
