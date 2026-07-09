class PurchaseOrderItem {
  PurchaseOrderItem({
    required this.id,
    required this.productId,
    required this.productName,
    required this.quantity,
    required this.quantityOutstanding,
    required this.unitPrice,
  });

  factory PurchaseOrderItem.fromJson(Map<String, dynamic> json) {
    return PurchaseOrderItem(
      id: json['id'] as String,
      productId: json['product'] as String,
      productName: json['product_name'] as String? ?? '',
      quantity: double.tryParse(json['quantity'].toString()) ?? 0,
      quantityOutstanding: double.tryParse(json['quantity_outstanding'].toString()) ?? 0,
      unitPrice: double.tryParse(json['unit_price'].toString()) ?? 0,
    );
  }

  final String id;
  final String productId;
  final String productName;
  final double quantity;
  final double quantityOutstanding;
  final double unitPrice;
}

class PurchaseOrder {
  PurchaseOrder({
    required this.id,
    required this.number,
    required this.supplierName,
    required this.status,
    required this.total,
    required this.balanceDue,
    required this.items,
  });

  factory PurchaseOrder.fromJson(Map<String, dynamic> json) {
    return PurchaseOrder(
      id: json['id'] as String,
      number: json['number'] as String,
      supplierName: json['supplier_name'] as String? ?? '',
      status: json['status'] as String,
      total: double.tryParse(json['total'].toString()) ?? 0,
      balanceDue: double.tryParse(json['balance_due'].toString()) ?? 0,
      items: (json['items'] as List? ?? [])
          .map((e) => PurchaseOrderItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final String id;
  final String number;
  final String supplierName;
  final String status;
  final double total;
  final double balanceDue;
  final List<PurchaseOrderItem> items;
}
