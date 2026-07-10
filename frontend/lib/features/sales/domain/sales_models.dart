class Quotation {
  Quotation({
    required this.id,
    required this.number,
    required this.customerName,
    required this.status,
    required this.total,
  });

  factory Quotation.fromJson(Map<String, dynamic> json) {
    return Quotation(
      id: json['id'] as String,
      number: json['number'] as String,
      customerName: json['customer_name'] as String? ?? '',
      status: json['status'] as String,
      total: double.tryParse(json['total'].toString()) ?? 0,
    );
  }

  final String id;
  final String number;
  final String customerName;
  final String status;
  final double total;
}

class SalesOrderLine {
  SalesOrderLine({
    required this.id,
    required this.productName,
    required this.quantity,
    required this.quantityInvoiced,
    required this.quantityOutstanding,
    required this.unitPrice,
  });

  factory SalesOrderLine.fromJson(Map<String, dynamic> json) {
    return SalesOrderLine(
      id: json['id'] as String,
      productName: json['product_name'] as String? ?? '',
      quantity: double.tryParse(json['quantity'].toString()) ?? 0,
      quantityInvoiced: double.tryParse(json['quantity_invoiced'].toString()) ?? 0,
      quantityOutstanding: double.tryParse(json['quantity_outstanding'].toString()) ?? 0,
      unitPrice: double.tryParse(json['unit_price'].toString()) ?? 0,
    );
  }

  final String id;
  final String productName;
  final double quantity;
  final double quantityInvoiced;
  final double quantityOutstanding;
  final double unitPrice;
}

class SalesOrder {
  SalesOrder({
    required this.id,
    required this.number,
    required this.customerName,
    required this.status,
    required this.total,
    required this.items,
  });

  factory SalesOrder.fromJson(Map<String, dynamic> json) {
    final rawItems = (json['items'] as List?) ?? const [];
    return SalesOrder(
      id: json['id'] as String,
      number: json['number'] as String,
      customerName: json['customer_name'] as String? ?? '',
      status: json['status'] as String,
      total: double.tryParse(json['total'].toString()) ?? 0,
      items: rawItems.map((e) => SalesOrderLine.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  final String id;
  final String number;
  final String customerName;
  final String status;
  final double total;
  final List<SalesOrderLine> items;

  /// Lines that still have quantity left to invoice.
  List<SalesOrderLine> get outstandingLines =>
      items.where((i) => i.quantityOutstanding > 0).toList();

  bool get canInvoice => status != 'cancelled' && outstandingLines.isNotEmpty;
}

class Invoice {
  Invoice({
    required this.id,
    required this.number,
    required this.customerName,
    required this.status,
    required this.total,
    required this.amountPaid,
    required this.balanceDue,
  });

  factory Invoice.fromJson(Map<String, dynamic> json) {
    return Invoice(
      id: json['id'] as String,
      number: json['number'] as String,
      customerName: json['customer_name'] as String? ?? '',
      status: json['status'] as String,
      total: double.tryParse(json['total'].toString()) ?? 0,
      amountPaid: double.tryParse(json['amount_paid'].toString()) ?? 0,
      balanceDue: double.tryParse(json['balance_due'].toString()) ?? 0,
    );
  }

  final String id;
  final String number;
  final String customerName;
  final String status;
  final double total;
  final double amountPaid;
  final double balanceDue;
}
