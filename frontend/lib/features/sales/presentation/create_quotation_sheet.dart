import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/line_item_editor.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../customers/providers/customer_providers.dart';
import '../../products/providers/product_providers.dart';
import '../providers/sales_providers.dart';

Future<void> showCreateQuotationSheet(BuildContext context) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => const _CreateQuotationSheet(),
  );
}

class _CreateQuotationSheet extends ConsumerStatefulWidget {
  const _CreateQuotationSheet();

  @override
  ConsumerState<_CreateQuotationSheet> createState() => _CreateQuotationSheetState();
}

class _CreateQuotationSheetState extends ConsumerState<_CreateQuotationSheet> {
  String? _customerId;
  List<LineItemDraft> _items = [];
  bool _submitting = false;

  Future<void> _submit() async {
    if (_customerId == null || _items.where((i) => i.isValid).isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a customer and at least one product line.')),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      await ref.read(salesRepositoryProvider).createQuotation(customerId: _customerId!, items: _items);
      ref.invalidate(quotationListProvider);
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
    final customersAsync = ref.watch(customerListProvider);
    final productsAsync = ref.watch(productListProvider);

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
            Text('New Quotation', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 20),
            customersAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, _) => const SizedBox.shrink(),
              data: (customers) => DropdownButtonFormField<String>(
                initialValue: _customerId,
                decoration: const InputDecoration(labelText: 'Customer'),
                items: customers.map((c) => DropdownMenuItem(value: c.id, child: Text(c.name))).toList(),
                onChanged: (v) => setState(() => _customerId = v),
              ),
            ),
            const SizedBox(height: 20),
            productsAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, _) => const SizedBox.shrink(),
              data: (products) => LineItemEditor(
                priceLabel: l10n.sellingPrice,
                products: products
                    .map((p) => ProductOption(id: p.id, label: '${p.name} (${p.sku})', defaultPrice: p.sellingPrice))
                    .toList(),
                onChanged: (items) => _items = items,
              ),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(l10n.save),
            ),
          ],
        ),
      ),
    );
  }
}
