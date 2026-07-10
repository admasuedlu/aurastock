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

/// Goods-receipt-based purchase trend; same shape as [SalesSummary] so the
/// UI can render both with one widget.
class PurchaseSummary {
  PurchaseSummary({required this.todayTotal, required this.monthTotal, required this.periodTotal, required this.series});

  factory PurchaseSummary.fromJson(Map<String, dynamic> json) {
    return PurchaseSummary(
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

class AbcClassSummary {
  AbcClassSummary({required this.abcClass, required this.productCount, required this.revenue, required this.revenuePct});

  factory AbcClassSummary.fromJson(Map<String, dynamic> json) {
    return AbcClassSummary(
      abcClass: json['abc_class'] as String,
      productCount: json['product_count'] as int? ?? 0,
      revenue: double.tryParse(json['revenue'].toString()) ?? 0,
      revenuePct: double.tryParse(json['revenue_pct'].toString()) ?? 0,
    );
  }

  final String abcClass;
  final int productCount;
  final double revenue;
  final double revenuePct;
}

class AbcRow {
  AbcRow({
    required this.productName,
    required this.productSku,
    required this.quantitySold,
    required this.revenue,
    required this.cumulativePct,
    required this.abcClass,
  });

  factory AbcRow.fromJson(Map<String, dynamic> json) {
    return AbcRow(
      productName: json['product_name'] as String,
      productSku: json['product_sku'] as String? ?? '',
      quantitySold: double.tryParse(json['quantity_sold'].toString()) ?? 0,
      revenue: double.tryParse(json['revenue'].toString()) ?? 0,
      cumulativePct: double.tryParse(json['cumulative_pct'].toString()) ?? 0,
      abcClass: json['abc_class'] as String,
    );
  }

  final String productName;
  final String productSku;
  final double quantitySold;
  final double revenue;
  final double cumulativePct;
  final String abcClass;
}

class AbcAnalysis {
  AbcAnalysis({required this.totalRevenue, required this.summary, required this.rows});

  factory AbcAnalysis.fromJson(Map<String, dynamic> json) {
    return AbcAnalysis(
      totalRevenue: double.tryParse(json['total_revenue'].toString()) ?? 0,
      summary: (json['summary'] as List).map((e) => AbcClassSummary.fromJson(e as Map<String, dynamic>)).toList(),
      rows: (json['rows'] as List).map((e) => AbcRow.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  final double totalRevenue;
  final List<AbcClassSummary> summary;
  final List<AbcRow> rows;
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
