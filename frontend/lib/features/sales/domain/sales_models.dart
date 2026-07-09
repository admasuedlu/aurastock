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

class SalesOrder {
  SalesOrder({
    required this.id,
    required this.number,
    required this.customerName,
    required this.status,
    required this.total,
  });

  factory SalesOrder.fromJson(Map<String, dynamic> json) {
    return SalesOrder(
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
