class Category {
  Category({required this.id, required this.name});
  factory Category.fromJson(Map<String, dynamic> json) =>
      Category(id: json['id'] as String, name: json['name'] as String);
  final String id;
  final String name;
}

class UnitOfMeasure {
  UnitOfMeasure({required this.id, required this.name, required this.symbol});
  factory UnitOfMeasure.fromJson(Map<String, dynamic> json) => UnitOfMeasure(
        id: json['id'] as String,
        name: json['name'] as String,
        symbol: json['symbol'] as String,
      );
  final String id;
  final String name;
  final String symbol;
}

class Product {
  Product({
    required this.id,
    required this.name,
    required this.sku,
    required this.barcode,
    required this.categoryName,
    required this.unitSymbol,
    required this.productType,
    required this.costPrice,
    required this.sellingPrice,
    required this.reorderLevel,
    required this.trackBatch,
    required this.trackExpiry,
    required this.isActive,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] as String,
      name: json['name'] as String,
      sku: json['sku'] as String,
      barcode: json['barcode'] as String? ?? '',
      categoryName: json['category_name'] as String? ?? '',
      unitSymbol: json['unit_symbol'] as String? ?? '',
      productType: json['product_type'] as String? ?? 'simple',
      costPrice: double.tryParse(json['cost_price'].toString()) ?? 0,
      sellingPrice: double.tryParse(json['selling_price'].toString()) ?? 0,
      reorderLevel: double.tryParse(json['reorder_level'].toString()) ?? 0,
      trackBatch: json['track_batch'] as bool? ?? false,
      trackExpiry: json['track_expiry'] as bool? ?? false,
      isActive: json['is_active'] as bool? ?? true,
    );
  }

  final String id;
  final String name;
  final String sku;
  final String barcode;
  final String categoryName;
  final String unitSymbol;
  final String productType;
  final double costPrice;
  final double sellingPrice;
  final double reorderLevel;
  final bool trackBatch;
  final bool trackExpiry;
  final bool isActive;

  bool get isBatchTracked => trackBatch || trackExpiry;
  bool get isBundle => productType == 'bundle';
}

class BundleComponent {
  BundleComponent({
    required this.id,
    required this.componentId,
    required this.componentName,
    required this.componentSku,
    required this.quantity,
  });

  factory BundleComponent.fromJson(Map<String, dynamic> json) {
    return BundleComponent(
      id: json['id'] as String,
      componentId: json['component'] as String,
      componentName: json['component_name'] as String? ?? '',
      componentSku: json['component_sku'] as String? ?? '',
      quantity: double.tryParse(json['quantity'].toString()) ?? 0,
    );
  }

  final String id;
  final String componentId;
  final String componentName;
  final String componentSku;
  final double quantity;
}
