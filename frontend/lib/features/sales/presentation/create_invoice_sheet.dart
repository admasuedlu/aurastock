import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/line_item_editor.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../customers/providers/customer_providers.dart';
import '../../inventory/providers/inventory_providers.dart';
import '../../products/providers/product_providers.dart';
import '../providers/sales_providers.dart';

Future<void> showCreateInvoiceSheet(BuildContext context) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => const _CreateInvoiceSheet(),
  );
}

class _CreateInvoiceSheet extends ConsumerStatefulWidget {
  const _CreateInvoiceSheet();

  @override
  ConsumerState<_CreateInvoiceSheet> createState() => _CreateInvoiceSheetState();
}

class _CreateInvoiceSheetState extends ConsumerState<_CreateInvoiceSheet> {
  String? _customerId;
  String? _warehouseId;
  List<LineItemDraft> _items = [];
  bool _submitting = false;

  Future<void> _submit() async {
    if (_customerId == null || _warehouseId == null || _items.where((i) => i.isValid).isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a customer, warehouse, and at least one product line.')),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      await ref.read(salesRepositoryProvider).createInvoice(
            customerId: _customerId!, warehouseId: _warehouseId!, items: _items,
          );
      ref.invalidate(invoiceListProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final customersAsync = ref.watch(customerListProvider);
    final warehousesAsync = ref.watch(warehouseListProvider);
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
            Text('New Invoice', style: Theme.of(context).textTheme.titleLarge),
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
            const SizedBox(height: 16),
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
            Text(
              'Confirming the invoice will deduct stock from the selected warehouse.',
              style: Theme.of(context).textTheme.bodySmall,
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
