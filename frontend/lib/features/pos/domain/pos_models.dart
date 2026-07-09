class PosSession {
  PosSession({
    required this.id,
    required this.warehouseId,
    required this.warehouseName,
    required this.status,
    required this.openingCash,
    required this.closingCash,
    required this.expectedCash,
    required this.cashVariance,
  });

  factory PosSession.fromJson(Map<String, dynamic> json) {
    return PosSession(
      id: json['id'] as String,
      warehouseId: json['warehouse'] as String,
      warehouseName: json['warehouse_name'] as String? ?? '',
      status: json['status'] as String,
      openingCash: double.tryParse(json['opening_cash'].toString()) ?? 0,
      closingCash: json['closing_cash'] == null ? null : double.tryParse(json['closing_cash'].toString()),
      expectedCash: json['expected_cash'] == null ? null : double.tryParse(json['expected_cash'].toString()),
      cashVariance: json['cash_variance'] == null ? null : double.tryParse(json['cash_variance'].toString()),
    );
  }

  final String id;
  final String warehouseId;
  final String warehouseName;
  final String status;
  final double openingCash;
  final double? closingCash;
  final double? expectedCash;
  final double? cashVariance;
}

class PosTransactionItem {
  PosTransactionItem({required this.productName, required this.quantity, required this.lineTotal});

  factory PosTransactionItem.fromJson(Map<String, dynamic> json) {
    return PosTransactionItem(
      productName: json['product_name'] as String? ?? '',
      quantity: double.tryParse(json['quantity'].toString()) ?? 0,
      lineTotal: double.tryParse(json['line_total'].toString()) ?? 0,
    );
  }

  final String productName;
  final double quantity;
  final double lineTotal;
}

class PosTransaction {
  PosTransaction({
    required this.id,
    required this.number,
    required this.customerName,
    required this.paymentMethod,
    required this.total,
    required this.amountTendered,
    required this.changeDue,
    required this.status,
    required this.items,
  });

  factory PosTransaction.fromJson(Map<String, dynamic> json) {
    return PosTransaction(
      id: json['id'] as String,
      number: json['number'] as String,
      customerName: json['customer_name'] as String? ?? 'Walk-in',
      paymentMethod: json['payment_method'] as String,
      total: double.tryParse(json['total'].toString()) ?? 0,
      amountTendered: double.tryParse(json['amount_tendered'].toString()) ?? 0,
      changeDue: double.tryParse(json['change_due'].toString()) ?? 0,
      status: json['status'] as String,
      items: (json['items'] as List? ?? [])
          .map((e) => PosTransactionItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final String id;
  final String number;
  final String customerName;
  final String paymentMethod;
  final double total;
  final double amountTendered;
  final double changeDue;
  final String status;
  final List<PosTransactionItem> items;
}
