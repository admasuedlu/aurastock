class Warehouse {
  Warehouse({required this.id, required this.name, required this.code});
  factory Warehouse.fromJson(Map<String, dynamic> json) => Warehouse(
        id: json['id'] as String,
        name: json['name'] as String,
        code: json['code'] as String,
      );
  final String id;
  final String name;
  final String code;
}

class StockItem {
  StockItem({
    required this.id,
    required this.productId,
    required this.productName,
    required this.productSku,
    required this.warehouseId,
    required this.warehouseName,
    required this.quantityOnHand,
    required this.availableQuantity,
    required this.averageCost,
    required this.reorderLevel,
    required this.isLowStock,
  });

  factory StockItem.fromJson(Map<String, dynamic> json) {
    return StockItem(
      id: json['id'] as String,
      productId: json['product'] as String,
      productName: json['product_name'] as String? ?? '',
      productSku: json['product_sku'] as String? ?? '',
      warehouseId: json['warehouse'] as String,
      warehouseName: json['warehouse_name'] as String? ?? '',
      quantityOnHand: double.tryParse(json['quantity_on_hand'].toString()) ?? 0,
      availableQuantity: double.tryParse(json['available_quantity'].toString()) ?? 0,
      averageCost: double.tryParse(json['average_cost'].toString()) ?? 0,
      reorderLevel: double.tryParse(json['reorder_level'].toString()) ?? 0,
      isLowStock: json['is_low_stock'] as bool? ?? false,
    );
  }

  final String id;
  final String productId;
  final String productName;
  final String productSku;
  final String warehouseId;
  final String warehouseName;
  final double quantityOnHand;
  final double availableQuantity;
  final double averageCost;
  final double reorderLevel;
  final bool isLowStock;

  double get stockValue => quantityOnHand * averageCost;
}

class StockMovement {
  StockMovement({
    required this.id,
    required this.movementType,
    required this.productName,
    required this.warehouseName,
    required this.quantity,
    required this.reference,
    required this.createdAt,
  });

  factory StockMovement.fromJson(Map<String, dynamic> json) {
    return StockMovement(
      id: json['id'] as String,
      movementType: json['movement_type'] as String,
      productName: json['product_name'] as String? ?? '',
      warehouseName: json['warehouse_name'] as String? ?? '',
      quantity: double.tryParse(json['quantity'].toString()) ?? 0,
      reference: json['reference'] as String? ?? '',
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String id;
  final String movementType;
  final String productName;
  final String warehouseName;
  final double quantity;
  final String reference;
  final DateTime createdAt;
}
