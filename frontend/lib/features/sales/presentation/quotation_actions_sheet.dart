import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../domain/sales_models.dart';
import '../providers/sales_providers.dart';

Future<void> showQuotationActionsSheet(BuildContext context, WidgetRef ref, Quotation quotation) {
  return showModalBottomSheet(
    context: context,
    builder: (context) => _QuotationActionsSheet(quotation: quotation),
  );
}

class _QuotationActionsSheet extends ConsumerStatefulWidget {
  const _QuotationActionsSheet({required this.quotation});
  final Quotation quotation;

  @override
  ConsumerState<_QuotationActionsSheet> createState() => _QuotationActionsSheetState();
}

class _QuotationActionsSheetState extends ConsumerState<_QuotationActionsSheet> {
  bool _busy = false;

  static const _nonConvertibleStatuses = {'converted', 'rejected', 'expired'};

  Future<void> _convert() async {
    setState(() => _busy = true);
    try {
      await ref.read(salesRepositoryProvider).convertQuotationToOrder(widget.quotation.id);
      ref.invalidate(quotationListProvider);
      ref.invalidate(salesOrderListProvider);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Converted to a sales order.')),
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
    final quotation = widget.quotation;
    final canConvert = !_nonConvertibleStatuses.contains(quotation.status);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(quotation.number, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(quotation.customerName),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total'),
                Text(currency.format(quotation.total), style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 20),
            if (_busy)
              const Center(child: CircularProgressIndicator())
            else if (canConvert)
              FilledButton.icon(
                onPressed: _convert,
                icon: const Icon(Icons.arrow_forward),
                label: const Text('Convert to Sales Order'),
              )
            else
              Text('This quotation is ${quotation.status} and cannot be converted.'),
          ],
        ),
      ),
    );
  }
}
