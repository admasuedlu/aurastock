import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../inventory/providers/inventory_providers.dart';
import '../domain/product.dart';
import '../providers/product_providers.dart';

Future<void> showBundleSheet(BuildContext context, Product bundle) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => _BundleSheet(bundle: bundle),
  );
}

class _BundleSheet extends ConsumerStatefulWidget {
  const _BundleSheet({required this.bundle});
  final Product bundle;

  @override
  ConsumerState<_BundleSheet> createState() => _BundleSheetState();
}

class _BundleSheetState extends ConsumerState<_BundleSheet> {
  List<BundleComponent>? _components;
  String? _componentId;
  final _qtyController = TextEditingController(text: '1');
  String? _warehouseId;
  final _assembleQtyController = TextEditingController(text: '1');
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _qtyController.dispose();
    _assembleQtyController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final comps = await ref.read(productRepositoryProvider).fetchBundleComponents(widget.bundle.id);
      if (mounted) setState(() => _components = comps);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _run(Future<void> Function() action, {String? done, bool pop = false}) async {
    setState(() => _busy = true);
    try {
      await action();
      if (pop && mounted) Navigator.of(context).pop();
      if (done != null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _addComponent() {
    if (_componentId == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Pick a component product.')));
      return;
    }
    final qty = double.tryParse(_qtyController.text) ?? 0;
    if (qty <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter a positive quantity.')));
      return;
    }
    final repo = ref.read(productRepositoryProvider);
    _run(() async {
      await repo.addBundleComponent(widget.bundle.id, _componentId!, qty);
      await _load();
      if (mounted) setState(() => _componentId = null);
    });
  }

  void _assemble() {
    if (_warehouseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Pick a warehouse.')));
      return;
    }
    final qty = double.tryParse(_assembleQtyController.text) ?? 0;
    if (qty <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter a positive quantity.')));
      return;
    }
    final repo = ref.read(productRepositoryProvider);
    _run(() async {
      await repo.assembleBundle(warehouseId: _warehouseId!, bundleId: widget.bundle.id, quantity: qty);
      ref.invalidate(stockItemListProvider);
    }, done: 'Assembled — components consumed, bundle stock added.', pop: true);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final products = (ref.watch(productListProvider).valueOrNull ?? const <Product>[])
        .where((p) => p.id != widget.bundle.id)
        .toList();
    final warehousesAsync = ref.watch(warehouseListProvider);
    final components = _components;

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
            Text('${widget.bundle.name} · components', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            if (components == null)
              const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator()))
            else if (components.isEmpty)
              const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('No components yet.'))
            else
              for (final c in components)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${c.quantity.toStringAsFixed(c.quantity == c.quantity.roundToDouble() ? 0 : 3)} × ${c.componentName}'),
                  subtitle: Text(c.componentSku),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline),
                    onPressed: _busy ? null : () => _run(() async {
                      await ref.read(productRepositoryProvider).removeBundleComponent(c.id);
                      await _load();
                    }),
                  ),
                ),
            const Divider(height: 24),
            Text('Add component', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _componentId,
                    decoration: const InputDecoration(labelText: 'Product', isDense: true),
                    items: products
                        .map((p) => DropdownMenuItem(value: p.id, child: Text('${p.name} (${p.sku})')))
                        .toList(),
                    onChanged: (v) => setState(() => _componentId = v),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 80,
                  child: TextField(
                    controller: _qtyController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    textAlign: TextAlign.right,
                    decoration: const InputDecoration(labelText: 'Qty', isDense: true),
                  ),
                ),
                IconButton(onPressed: _busy ? null : _addComponent, icon: const Icon(Icons.add)),
              ],
            ),
            const Divider(height: 24),
            Text('Assemble', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            warehousesAsync.when(
              loading: () => const LinearProgressIndicator(),
              error: (_, _) => Text(l10n.errorGeneric),
              data: (warehouses) => DropdownButtonFormField<String>(
                initialValue: _warehouseId,
                decoration: InputDecoration(labelText: l10n.warehouse),
                items: warehouses.map((w) => DropdownMenuItem(value: w.id, child: Text(w.name))).toList(),
                onChanged: (v) => setState(() => _warehouseId = v),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _assembleQtyController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Quantity to assemble'),
            ),
            const SizedBox(height: 8),
            Text(
              'Consumes each component × this quantity from the chosen warehouse and '
              'adds the assembled bundles to stock at their combined component cost.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _busy ? null : _assemble,
              icon: const Icon(Icons.precision_manufacturing_outlined),
              label: const Text('Assemble'),
            ),
          ],
        ),
      ),
    );
  }
}
