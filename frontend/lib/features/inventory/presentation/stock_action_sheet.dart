import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../products/providers/product_providers.dart';
import '../providers/inventory_providers.dart';

enum StockActionType { stockIn, stockOut, transfer, adjustment }

Future<void> showStockActionSheet(BuildContext context, StockActionType type) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => _StockActionSheet(type: type),
  );
}

class _StockActionSheet extends ConsumerStatefulWidget {
  const _StockActionSheet({required this.type});
  final StockActionType type;

  @override
  ConsumerState<_StockActionSheet> createState() => _StockActionSheetState();
}

class _StockActionSheetState extends ConsumerState<_StockActionSheet> {
  final _formKey = GlobalKey<FormState>();
  final _quantityController = TextEditingController();
  final _unitCostController = TextEditingController(text: '0');
  final _referenceController = TextEditingController();
  final _reasonController = TextEditingController();
  String? _productId;
  String? _warehouseId;
  String? _toWarehouseId;
  bool _submitting = false;

  @override
  void dispose() {
    _quantityController.dispose();
    _unitCostController.dispose();
    _referenceController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  String _title(AppLocalizations l10n) {
    switch (widget.type) {
      case StockActionType.stockIn:
        return l10n.stockIn;
      case StockActionType.stockOut:
        return l10n.stockOut;
      case StockActionType.transfer:
        return l10n.stockTransfer;
      case StockActionType.adjustment:
        return l10n.stockAdjustment;
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_productId == null || _warehouseId == null) return;
    if (widget.type == StockActionType.transfer && _toWarehouseId == null) return;

    setState(() => _submitting = true);
    final repo = ref.read(inventoryRepositoryProvider);
    final quantity = double.tryParse(_quantityController.text) ?? 0;
    try {
      switch (widget.type) {
        case StockActionType.stockIn:
          await repo.stockIn(
            warehouseId: _warehouseId!,
            productId: _productId!,
            quantity: quantity,
            unitCost: double.tryParse(_unitCostController.text) ?? 0,
            reference: _referenceController.text.trim(),
            reason: _reasonController.text.trim(),
          );
          break;
        case StockActionType.stockOut:
          await repo.stockOut(
            warehouseId: _warehouseId!,
            productId: _productId!,
            quantity: quantity,
            reference: _referenceController.text.trim(),
            reason: _reasonController.text.trim(),
          );
          break;
        case StockActionType.transfer:
          await repo.transferStock(
            fromWarehouseId: _warehouseId!,
            toWarehouseId: _toWarehouseId!,
            productId: _productId!,
            quantity: quantity,
            reference: _referenceController.text.trim(),
            reason: _reasonController.text.trim(),
          );
          break;
        case StockActionType.adjustment:
          await repo.adjustStock(
            warehouseId: _warehouseId!,
            productId: _productId!,
            quantityDelta: quantity,
            reason: _reasonController.text.trim(),
          );
          break;
      }
      ref.invalidate(stockItemListProvider);
      ref.invalidate(lowStockItemListProvider);
      ref.invalidate(movementListProvider);
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
    final productsAsync = ref.watch(productListProvider);
    final warehousesAsync = ref.watch(warehouseListProvider);
    final isAdjustment = widget.type == StockActionType.adjustment;

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
            Text(_title(l10n), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 20),
            productsAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => const SizedBox.shrink(),
              data: (products) => DropdownButtonFormField<String>(
                initialValue: _productId,
                decoration: const InputDecoration(labelText: 'Product'),
                items: products.map((p) => DropdownMenuItem(value: p.id, child: Text('${p.name} (${p.sku})'))).toList(),
                onChanged: (value) => setState(() => _productId = value),
                validator: (v) => v == null ? l10n.requiredField : null,
              ),
            ),
            const SizedBox(height: 16),
            warehousesAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, __) => const SizedBox.shrink(),
              data: (warehouses) => DropdownButtonFormField<String>(
                initialValue: _warehouseId,
                decoration: InputDecoration(
                  labelText: widget.type == StockActionType.transfer ? 'From warehouse' : l10n.warehouse,
                ),
                items: warehouses.map((w) => DropdownMenuItem(value: w.id, child: Text(w.name))).toList(),
                onChanged: (value) => setState(() => _warehouseId = value),
                validator: (v) => v == null ? l10n.requiredField : null,
              ),
            ),
            if (widget.type == StockActionType.transfer) ...[
              const SizedBox(height: 16),
              warehousesAsync.when(
                loading: () => const LinearProgressIndicator(),
                error: (_, __) => const SizedBox.shrink(),
                data: (warehouses) => DropdownButtonFormField<String>(
                  initialValue: _toWarehouseId,
                  decoration: const InputDecoration(labelText: 'To warehouse'),
                  items: warehouses.map((w) => DropdownMenuItem(value: w.id, child: Text(w.name))).toList(),
                  onChanged: (value) => setState(() => _toWarehouseId = value),
                  validator: (v) => v == null ? l10n.requiredField : null,
                ),
              ),
            ],
            const SizedBox(height: 16),
            TextFormField(
              controller: _quantityController,
              decoration: InputDecoration(labelText: isAdjustment ? '${l10n.quantity} (+/-)' : l10n.quantity),
              keyboardType: const TextInputType.numberWithOptions(signed: true, decimal: true),
              validator: (v) => (v == null || v.isEmpty) ? l10n.requiredField : null,
            ),
            if (widget.type == StockActionType.stockIn) ...[
              const SizedBox(height: 16),
              TextFormField(
                controller: _unitCostController,
                decoration: InputDecoration(labelText: l10n.unitCost),
                keyboardType: TextInputType.number,
              ),
            ],
            if (!isAdjustment) ...[
              const SizedBox(height: 16),
              TextFormField(
                controller: _referenceController,
                decoration: InputDecoration(labelText: l10n.reference),
              ),
            ],
            const SizedBox(height: 16),
            TextFormField(
              controller: _reasonController,
              decoration: InputDecoration(labelText: l10n.reason),
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
