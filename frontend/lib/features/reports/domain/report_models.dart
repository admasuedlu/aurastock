class SalesTrendPoint {
  SalesTrendPoint({required this.date, required this.total});
  factory SalesTrendPoint.fromJson(Map<String, dynamic> json) => SalesTrendPoint(
        date: DateTime.parse(json['date'] as String),
        total: double.tryParse(json['total'].toString()) ?? 0,
      );
  final DateTime date;
  final double total;
}

class SalesSummary {
  SalesSummary({required this.todayTotal, required this.monthTotal, required this.periodTotal, required this.series});

  factory SalesSummary.fromJson(Map<String, dynamic> json) {
    return SalesSummary(
      todayTotal: double.tryParse(json['today_total'].toString()) ?? 0,
      monthTotal: double.tryParse(json['month_total'].toString()) ?? 0,
      periodTotal: double.tryParse(json['period_total'].toString()) ?? 0,
      series: (json['series'] as List).map((e) => SalesTrendPoint.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  final double todayTotal;
  final double monthTotal;
  final double periodTotal;
  final List<SalesTrendPoint> series;
}

class TopProductRow {
  TopProductRow({required this.productName, required this.productSku, required this.quantitySold, required this.revenue});

  factory TopProductRow.fromJson(Map<String, dynamic> json) {
    return TopProductRow(
      productName: json['product_name'] as String,
      productSku: json['product_sku'] as String? ?? '',
      quantitySold: double.tryParse(json['quantity_sold'].toString()) ?? 0,
      revenue: double.tryParse(json['revenue'].toString()) ?? 0,
    );
  }

  final String productName;
  final String productSku;
  final double quantitySold;
  final double revenue;
}

class ValuationRow {
  ValuationRow({
    required this.productName,
    required this.productSku,
    required this.warehouseName,
    required this.quantityOnHand,
    required this.value,
  });

  factory ValuationRow.fromJson(Map<String, dynamic> json) {
    return ValuationRow(
      productName: json['product_name'] as String,
      productSku: json['product_sku'] as String? ?? '',
      warehouseName: json['warehouse_name'] as String,
      quantityOnHand: double.tryParse(json['quantity_on_hand'].toString()) ?? 0,
      value: double.tryParse(json['value'].toString()) ?? 0,
    );
  }

  final String productName;
  final String productSku;
  final String warehouseName;
  final double quantityOnHand;
  final double value;
}

class InventoryValuation {
  InventoryValuation({required this.totalValue, required this.rows});

  factory InventoryValuation.fromJson(Map<String, dynamic> json) {
    return InventoryValuation(
      totalValue: double.tryParse(json['total_value'].toString()) ?? 0,
      rows: (json['rows'] as List).map((e) => ValuationRow.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  final double totalValue;
  final List<ValuationRow> rows;
}

class DeadStockRow {
  DeadStockRow({
    required this.productName,
    required this.productSku,
    required this.warehouseName,
    required this.quantityOnHand,
    required this.value,
    required this.lastSoldAt,
  });

  factory DeadStockRow.fromJson(Map<String, dynamic> json) {
    return DeadStockRow(
      productName: json['product_name'] as String,
      productSku: json['product_sku'] as String? ?? '',
      warehouseName: json['warehouse_name'] as String,
      quantityOnHand: double.tryParse(json['quantity_on_hand'].toString()) ?? 0,
      value: double.tryParse(json['value'].toString()) ?? 0,
      lastSoldAt: json['last_sold_at'] as String?,
    );
  }

  final String productName;
  final String productSku;
  final String warehouseName;
  final double quantityOnHand;
  final double value;
  final String? lastSoldAt;
}
