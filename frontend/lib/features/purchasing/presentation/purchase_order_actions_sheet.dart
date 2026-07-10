import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../domain/purchasing_models.dart';
import '../providers/purchasing_providers.dart';
import 'receive_goods_sheet.dart';

Future<void> showPurchaseOrderActionsSheet(BuildContext context, WidgetRef ref, PurchaseOrder order) {
  return showModalBottomSheet(
    context: context,
    builder: (context) => _PurchaseOrderActionsSheet(order: order),
  );
}

class _PurchaseOrderActionsSheet extends ConsumerStatefulWidget {
  const _PurchaseOrderActionsSheet({required this.order});
  final PurchaseOrder order;

  @override
  ConsumerState<_PurchaseOrderActionsSheet> createState() => _PurchaseOrderActionsSheetState();
}

class _PurchaseOrderActionsSheetState extends ConsumerState<_PurchaseOrderActionsSheet> {
  bool _busy = false;

  Future<void> _send() async {
    setState(() => _busy = true);
    try {
      await ref.read(purchasingRepositoryProvider).sendPurchaseOrder(widget.order.id);
      ref.invalidate(purchaseOrderListProvider);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Sent — the supplier can now see it in the portal.')),
        );
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _recordPayment() async {
    final controller = TextEditingController(text: widget.order.balanceDue.toStringAsFixed(2));
    final amount = await showDialog<double>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Record payment'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Amount (ETB)'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(context, double.tryParse(controller.text)),
            child: const Text('Record'),
          ),
        ],
      ),
    );
    if (amount == null || amount <= 0) return;

    setState(() => _busy = true);
    try {
      await ref.read(purchasingRepositoryProvider).recordPayment(widget.order.id, amount: amount, method: 'bank_transfer');
      ref.invalidate(purchaseOrderListProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
    final order = widget.order;
    final canReceive = order.status != 'received' && order.status != 'cancelled';
    final canPay = order.balanceDue > 0;
    final canSend = order.status == 'draft';

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(order.number, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(order.supplierName),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total'),
                Text(currency.format(order.total), style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Balance due'),
                Text(currency.format(order.balanceDue)),
              ],
            ),
            const SizedBox(height: 20),
            if (_busy)
              const Center(child: CircularProgressIndicator())
            else ...[
              if (canSend)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: FilledButton.icon(
                    onPressed: _send,
                    icon: const Icon(Icons.send_outlined),
                    label: const Text('Send to Supplier'),
                  ),
                ),
              if (canReceive)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: FilledButton.icon(
                    onPressed: () {
                      Navigator.of(context).pop();
                      showReceiveGoodsSheet(context, order);
                    },
                    icon: const Icon(Icons.inventory_2_outlined),
                    label: const Text('Receive goods'),
                  ),
                ),
              if (canPay)
                OutlinedButton.icon(
                  onPressed: _recordPayment,
                  icon: const Icon(Icons.payments_outlined),
                  label: const Text('Record payment'),
                ),
              if (!canReceive && !canPay) const Text('This order is fully received and paid.'),
            ],
          ],
        ),
      ),
    );
  }
}
