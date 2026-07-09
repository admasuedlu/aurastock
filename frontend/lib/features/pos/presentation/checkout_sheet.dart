import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../customers/providers/customer_providers.dart';
import '../providers/pos_providers.dart';

Future<void> showCheckoutSheet(BuildContext context, String sessionId) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => CheckoutSheet(sessionId: sessionId),
  );
}

const _paymentMethods = [
  ('cash', 'Cash'),
  ('bank_transfer', 'Bank transfer'),
  ('telebirr', 'Telebirr'),
  ('cbe_pay', 'CBE Pay'),
  ('mpesa', 'M-Pesa'),
  ('amole', 'Amole'),
];

class CheckoutSheet extends ConsumerStatefulWidget {
  const CheckoutSheet({super.key, required this.sessionId});
  final String sessionId;

  @override
  ConsumerState<CheckoutSheet> createState() => _CheckoutSheetState();
}

class _CheckoutSheetState extends ConsumerState<CheckoutSheet> {
  String _paymentMethod = 'cash';
  String? _customerId;
  late final TextEditingController _tenderedController;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    final total = ref.read(cartControllerProvider.notifier).total;
    _tenderedController = TextEditingController(text: total.toStringAsFixed(2));
  }

  @override
  void dispose() {
    _tenderedController.dispose();
    super.dispose();
  }

  Future<void> _complete() async {
    final cart = ref.read(cartControllerProvider);
    if (cart.isEmpty) return;
    final tendered = double.tryParse(_tenderedController.text) ?? 0;
    final total = ref.read(cartControllerProvider.notifier).total;
    if (tendered < total) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Amount tendered is less than the total.')),
      );
      return;
    }

    setState(() => _submitting = true);
    try {
      final txn = await ref.read(posRepositoryProvider).createTransaction(
            sessionId: widget.sessionId,
            customerId: _customerId,
            paymentMethod: _paymentMethod,
            amountTendered: tendered,
            items: cart
                .map((item) => {
                      'product': item.productId,
                      'quantity': item.quantity,
                      'unit_price': item.unitPrice,
                      'tax_percent': item.taxPercent,
                    })
                .toList(),
          );
      ref.read(cartControllerProvider.notifier).clear();
      ref.invalidate(sessionTransactionsProvider(widget.sessionId));
      if (mounted) {
        Navigator.of(context).pop();
        final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: Text('Sale complete — ${txn.number}'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Total: ${currency.format(txn.total)}'),
                if (txn.paymentMethod == 'cash') Text('Change due: ${currency.format(txn.changeDue)}'),
              ],
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text('Done')),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = ref.watch(cartControllerProvider);
    final cartNotifier = ref.read(cartControllerProvider.notifier);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
    final customersAsync = ref.watch(customerListProvider);

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
            Text('Checkout', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            for (final item in cart)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Expanded(child: Text('${item.productName} x${item.quantity}')),
                    Text(currency.format(item.lineTotal)),
                  ],
                ),
              ),
            const Divider(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [const Text('Subtotal'), Text(currency.format(cartNotifier.subtotal))],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [const Text('Tax'), Text(currency.format(cartNotifier.taxTotal))],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)),
                Text(currency.format(cartNotifier.total), style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 16),
            customersAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => const SizedBox.shrink(),
              data: (customers) => DropdownButtonFormField<String>(
                initialValue: _customerId,
                decoration: const InputDecoration(labelText: 'Customer (optional — walk-in)'),
                items: customers.map((c) => DropdownMenuItem(value: c.id, child: Text(c.name))).toList(),
                onChanged: (v) => setState(() => _customerId = v),
              ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _paymentMethod,
              decoration: const InputDecoration(labelText: 'Payment method'),
              items: _paymentMethods
                  .map((m) => DropdownMenuItem(value: m.$1, child: Text(m.$2)))
                  .toList(),
              onChanged: (v) => setState(() => _paymentMethod = v ?? 'cash'),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _tenderedController,
              decoration: const InputDecoration(labelText: 'Amount tendered (ETB)'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _submitting ? null : _complete,
              child: _submitting
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Complete Sale'),
            ),
          ],
        ),
      ),
    );
  }
}
