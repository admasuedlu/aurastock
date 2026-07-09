import 'package:flutter/material.dart';

class LineItemDraft {
  LineItemDraft({this.productId, this.quantity = 1, this.unitPrice = 0});

  String? productId;
  double quantity;
  double unitPrice;

  bool get isValid => productId != null && quantity > 0;
}

class ProductOption {
  ProductOption({required this.id, required this.label, required this.defaultPrice});
  final String id;
  final String label;
  final double defaultPrice;
}

/// Editable list of (product, quantity, unit price) rows shared by the
/// sales-order / invoice / purchase-order creation forms.
class LineItemEditor extends StatefulWidget {
  const LineItemEditor({
    super.key,
    required this.products,
    required this.onChanged,
    this.priceLabel = 'Price',
  });

  final List<ProductOption> products;
  final ValueChanged<List<LineItemDraft>> onChanged;
  final String priceLabel;

  @override
  State<LineItemEditor> createState() => _LineItemEditorState();
}

class _LineItemEditorState extends State<LineItemEditor> {
  final List<LineItemDraft> _items = [LineItemDraft()];
  final List<TextEditingController> _qtyControllers = [TextEditingController(text: '1')];
  final List<TextEditingController> _priceControllers = [TextEditingController(text: '0')];

  @override
  void dispose() {
    for (final c in _qtyControllers) {
      c.dispose();
    }
    for (final c in _priceControllers) {
      c.dispose();
    }
    super.dispose();
  }

  void _notify() => widget.onChanged(List.unmodifiable(_items));

  void _addRow() {
    setState(() {
      _items.add(LineItemDraft());
      _qtyControllers.add(TextEditingController(text: '1'));
      _priceControllers.add(TextEditingController(text: '0'));
    });
    _notify();
  }

  void _removeRow(int index) {
    setState(() {
      _items.removeAt(index);
      _qtyControllers.removeAt(index).dispose();
      _priceControllers.removeAt(index).dispose();
    });
    _notify();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (int i = 0; i < _items.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: DropdownButtonFormField<String>(
                    initialValue: _items[i].productId,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Product'),
                    items: widget.products
                        .map((p) => DropdownMenuItem(value: p.id, child: Text(p.label, overflow: TextOverflow.ellipsis)))
                        .toList(),
                    onChanged: (value) {
                      final product = widget.products.firstWhere((p) => p.id == value);
                      setState(() {
                        _items[i].productId = value;
                        _items[i].unitPrice = product.defaultPrice;
                        _priceControllers[i].text = product.defaultPrice.toStringAsFixed(2);
                      });
                      _notify();
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  flex: 1,
                  child: TextFormField(
                    controller: _qtyControllers[i],
                    decoration: const InputDecoration(labelText: 'Qty'),
                    keyboardType: TextInputType.number,
                    onChanged: (v) {
                      _items[i].quantity = double.tryParse(v) ?? 0;
                      _notify();
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  flex: 2,
                  child: TextFormField(
                    controller: _priceControllers[i],
                    decoration: InputDecoration(labelText: widget.priceLabel),
                    keyboardType: TextInputType.number,
                    onChanged: (v) {
                      _items[i].unitPrice = double.tryParse(v) ?? 0;
                      _notify();
                    },
                  ),
                ),
                if (_items.length > 1)
                  IconButton(
                    icon: const Icon(Icons.remove_circle_outline),
                    onPressed: () => _removeRow(i),
                  ),
              ],
            ),
          ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: _addRow,
            icon: const Icon(Icons.add),
            label: const Text('Add line'),
          ),
        ),
      ],
    );
  }
}
