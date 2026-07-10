class ReorderSuggestion {
  ReorderSuggestion({
    required this.productId,
    required this.productName,
    required this.productSku,
    required this.warehouseName,
    required this.availableQuantity,
    required this.reorderLevel,
    required this.avgDailySales,
    required this.suggestedQuantity,
  });

  factory ReorderSuggestion.fromJson(Map<String, dynamic> json) {
    return ReorderSuggestion(
      productId: json['product_id'] as String,
      productName: json['product_name'] as String,
      productSku: json['product_sku'] as String? ?? '',
      warehouseName: json['warehouse_name'] as String,
      availableQuantity: double.tryParse(json['available_quantity'].toString()) ?? 0,
      reorderLevel: double.tryParse(json['reorder_level'].toString()) ?? 0,
      avgDailySales: double.tryParse(json['avg_daily_sales'].toString()) ?? 0,
      suggestedQuantity: double.tryParse(json['suggested_quantity'].toString()) ?? 0,
    );
  }

  final String productId;
  final String productName;
  final String productSku;
  final String warehouseName;
  final double availableQuantity;
  final double reorderLevel;
  final double avgDailySales;
  final double suggestedQuantity;
}

class DemandPoint {
  DemandPoint({required this.date, required this.quantity});
  factory DemandPoint.fromJson(Map<String, dynamic> json) => DemandPoint(
        date: DateTime.parse(json['date'] as String),
        quantity: double.tryParse(json['quantity'].toString()) ?? 0,
      );
  final DateTime date;
  final double quantity;
}

class DemandForecast {
  DemandForecast({
    required this.productName,
    required this.avgDailyDemand,
    required this.trend,
    required this.history,
    required this.forecast,
  });

  factory DemandForecast.fromJson(Map<String, dynamic> json) {
    return DemandForecast(
      productName: json['product_name'] as String,
      avgDailyDemand: double.tryParse(json['avg_daily_demand'].toString()) ?? 0,
      trend: json['trend'] as String,
      history: (json['history'] as List).map((e) => DemandPoint.fromJson(e as Map<String, dynamic>)).toList(),
      forecast: (json['forecast'] as List).map((e) => DemandPoint.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  final String productName;
  final double avgDailyDemand;
  final String trend;
  final List<DemandPoint> history;
  final List<DemandPoint> forecast;
}

class AnomalyRow {
  AnomalyRow({
    required this.productName,
    required this.warehouseName,
    required this.quantity,
    required this.typicalQuantity,
    required this.reference,
    required this.occurredAt,
  });

  factory AnomalyRow.fromJson(Map<String, dynamic> json) {
    return AnomalyRow(
      productName: json['product_name'] as String,
      warehouseName: json['warehouse_name'] as String,
      quantity: double.tryParse(json['quantity'].toString()) ?? 0,
      typicalQuantity: double.tryParse(json['typical_quantity'].toString()) ?? 0,
      reference: json['reference'] as String? ?? '',
      occurredAt: DateTime.parse(json['occurred_at'] as String),
    );
  }

  final String productName;
  final String warehouseName;
  final double quantity;
  final double typicalQuantity;
  final String reference;
  final DateTime occurredAt;
}
