import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../domain/sales_models.dart';
import '../providers/sales_providers.dart';

Future<void> showInvoiceActionsSheet(BuildContext context, WidgetRef ref, Invoice invoice) {
  return showModalBottomSheet(
    context: context,
    builder: (context) => _InvoiceActionsSheet(invoice: invoice),
  );
}

class _InvoiceActionsSheet extends ConsumerStatefulWidget {
  const _InvoiceActionsSheet({required this.invoice});
  final Invoice invoice;

  @override
  ConsumerState<_InvoiceActionsSheet> createState() => _InvoiceActionsSheetState();
}

class _InvoiceActionsSheetState extends ConsumerState<_InvoiceActionsSheet> {
  bool _busy = false;

  Future<void> _confirm() async {
    setState(() => _busy = true);
    try {
      await ref.read(salesRepositoryProvider).confirmInvoice(widget.invoice.id);
      ref.invalidate(invoiceListProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _recordPayment() async {
    final controller = TextEditingController(text: widget.invoice.balanceDue.toStringAsFixed(2));
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
      await ref.read(salesRepositoryProvider).recordPayment(widget.invoice.id, amount: amount, method: 'cash');
      ref.invalidate(invoiceListProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _payOnline() async {
    setState(() => _busy = true);
    Map<String, dynamic> intent;
    try {
      intent = await ref.read(salesRepositoryProvider).createPaymentIntent(widget.invoice.id);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
      return;
    }
    if (!mounted) return;
    setState(() => _busy = false);

    final pay = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Online payment (sandbox)'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('A real gateway would send the customer to this checkout link. '
                'There is no live provider here, so you can simulate the payer completing it.'),
            const SizedBox(height: 12),
            SelectableText(intent['checkout_url'] as String? ?? '',
                style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Close')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Simulate payment')),
        ],
      ),
    );
    if (pay != true) return;

    setState(() => _busy = true);
    try {
      await ref.read(salesRepositoryProvider).simulatePaymentCallback(intent['id'] as String);
      ref.invalidate(invoiceListProvider);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Payment recorded (sandbox).')),
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
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
    final invoice = widget.invoice;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(invoice.number, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(invoice.customerName),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total'),
                Text(currency.format(invoice.total), style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Balance due'),
                Text(currency.format(invoice.balanceDue)),
              ],
            ),
            const SizedBox(height: 20),
            if (_busy)
              const Center(child: CircularProgressIndicator())
            else ...[
              if (invoice.status == 'draft')
                FilledButton.icon(
                  onPressed: _confirm,
                  icon: const Icon(Icons.check_circle_outline),
                  label: const Text('Confirm invoice (deducts stock)'),
                ),
              if (invoice.status == 'confirmed' || invoice.status == 'partially_paid') ...[
                FilledButton.icon(
                  onPressed: _recordPayment,
                  icon: const Icon(Icons.payments_outlined),
                  label: const Text('Record payment'),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _payOnline,
                  icon: const Icon(Icons.link_outlined),
                  label: const Text('Pay online (sandbox)'),
                ),
              ],
              if (invoice.status == 'paid')
                const Text('This invoice is fully paid.'),
            ],
          ],
        ),
      ),
    );
  }
}
