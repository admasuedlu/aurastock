import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../providers/product_providers.dart';

Future<void> showProductFormSheet(BuildContext context) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => const _ProductFormSheet(),
  );
}

class _ProductFormSheet extends ConsumerStatefulWidget {
  const _ProductFormSheet();

  @override
  ConsumerState<_ProductFormSheet> createState() => _ProductFormSheetState();
}

class _ProductFormSheetState extends ConsumerState<_ProductFormSheet> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _barcodeController = TextEditingController();
  final _costController = TextEditingController(text: '0');
  final _priceController = TextEditingController(text: '0');
  final _reorderController = TextEditingController(text: '0');
  String? _categoryId;
  String? _unitId;
  bool _trackBatch = false;
  bool _trackExpiry = false;
  bool _trackSerial = false;
  bool _isBundle = false;
  bool _submitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _barcodeController.dispose();
    _costController.dispose();
    _priceController.dispose();
    _reorderController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate() || _unitId == null) return;
    setState(() => _submitting = true);
    try {
      await ref.read(productRepositoryProvider).createProduct(
            name: _nameController.text.trim(),
            categoryId: _categoryId,
            unitId: _unitId!,
            barcode: _barcodeController.text.trim(),
            costPrice: double.tryParse(_costController.text) ?? 0,
            sellingPrice: double.tryParse(_priceController.text) ?? 0,
            reorderLevel: double.tryParse(_reorderController.text) ?? 0,
            trackBatch: _trackBatch,
            trackExpiry: _trackExpiry,
            trackSerial: _trackSerial,
            isBundle: _isBundle,
          );
      ref.invalidate(productListProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).errorGeneric)),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final categoriesAsync = ref.watch(categoryListProvider);
    final unitsAsync = ref.watch(unitListProvider);

    return Padding(
      padding: EdgeInsets.only(
        left: 20, right: 20, top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(l10n.addProduct, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 20),
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'Product name'),
              validator: (v) => (v == null || v.isEmpty) ? l10n.requiredField : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _barcodeController,
              decoration: const InputDecoration(
                labelText: 'Barcode (optional)',
                prefixIcon: Icon(Icons.qr_code_2_outlined),
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            categoriesAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => const SizedBox.shrink(),
              data: (categories) => DropdownButtonFormField<String>(
                initialValue: _categoryId,
                decoration: InputDecoration(labelText: l10n.category),
                items: categories
                    .map((c) => DropdownMenuItem(value: c.id, child: Text(c.name)))
                    .toList(),
                onChanged: (value) => setState(() => _categoryId = value),
              ),
            ),
            const SizedBox(height: 16),
            unitsAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => const SizedBox.shrink(),
              data: (units) => DropdownButtonFormField<String>(
                initialValue: _unitId,
                decoration: InputDecoration(labelText: l10n.unit),
                items: units
                    .map((u) => DropdownMenuItem(value: u.id, child: Text('${u.name} (${u.symbol})')))
                    .toList(),
                onChanged: (value) => setState(() => _unitId = value),
                validator: (v) => v == null ? l10n.requiredField : null,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _costController,
                    decoration: InputDecoration(labelText: l10n.costPrice),
                    keyboardType: TextInputType.number,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _priceController,
                    decoration: InputDecoration(labelText: l10n.sellingPrice),
                    keyboardType: TextInputType.number,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _reorderController,
              decoration: InputDecoration(labelText: l10n.reorderLevel),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 8),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Track batches / lots'),
              subtitle: const Text('Receive and sell this product by batch number'),
              value: _trackBatch,
              onChanged: (v) => setState(() {
                _trackBatch = v;
                if (!v) _trackExpiry = false;
                if (v) _trackSerial = false;
              }),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Track expiry dates'),
              subtitle: const Text('Sell earliest-expiry batches first (FEFO)'),
              value: _trackExpiry,
              onChanged: (v) => setState(() {
                _trackExpiry = v;
                if (v) {
                  _trackBatch = true;
                  _trackSerial = false;
                }
              }),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Track serial numbers'),
              subtitle: const Text('Each unit individually identified (mutually exclusive with batches)'),
              value: _trackSerial,
              onChanged: (v) => setState(() {
                _trackSerial = v;
                if (v) {
                  _trackBatch = false;
                  _trackExpiry = false;
                }
              }),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Bundle / kit'),
              subtitle: const Text('Assembled from component products'),
              value: _isBundle,
              onChanged: (v) => setState(() => _isBundle = v),
            ),
            const SizedBox(height: 24),
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
