import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/line_item_editor.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../products/providers/product_providers.dart';
import '../../suppliers/providers/supplier_providers.dart';
import '../providers/purchasing_providers.dart';

Future<void> showCreatePurchaseRequestSheet(BuildContext context) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => const _CreatePurchaseRequestSheet(),
  );
}

class _CreatePurchaseRequestSheet extends ConsumerStatefulWidget {
  const _CreatePurchaseRequestSheet();

  @override
  ConsumerState<_CreatePurchaseRequestSheet> createState() => _CreatePurchaseRequestSheetState();
}

class _CreatePurchaseRequestSheetState extends ConsumerState<_CreatePurchaseRequestSheet> {
  String? _supplierId;
  List<LineItemDraft> _items = [];
  bool _submitting = false;

  Future<void> _submit() async {
    if (_items.where((i) => i.isValid).isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Add at least one product line.')),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      await ref.read(purchasingRepositoryProvider).createPurchaseRequest(
            supplierId: _supplierId, items: _items,
          );
      ref.invalidate(purchaseRequestListProvider);
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
    final suppliersAsync = ref.watch(supplierListProvider);
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
            Text('New Purchase Request', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              'Request goods for approval before an order is placed. A supplier is '
              'optional now — it can be chosen when the request is turned into an order.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            suppliersAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => const SizedBox.shrink(),
              data: (suppliers) => DropdownButtonFormField<String>(
                initialValue: _supplierId,
                decoration: const InputDecoration(labelText: 'Preferred supplier (optional)'),
                items: suppliers.map((s) => DropdownMenuItem(value: s.id, child: Text(s.name))).toList(),
                onChanged: (v) => setState(() => _supplierId = v),
              ),
            ),
            const SizedBox(height: 20),
            productsAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => const SizedBox.shrink(),
              data: (products) => LineItemEditor(
                priceLabel: l10n.costPrice,
                products: products
                    .map((p) => ProductOption(id: p.id, label: '${p.name} (${p.sku})', defaultPrice: p.costPrice))
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
