import 'package:dio/dio.dart';

import '../domain/inventory_models.dart';

class InventoryRepository {
  InventoryRepository(this._dio);
  final Dio _dio;

  Future<List<Warehouse>> fetchWarehouses() async {
    final response = await _dio.get('/warehouses/');
    final results = response.data['results'] as List;
    return results.map((e) => Warehouse.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Warehouse> createWarehouse({required String name, required String code}) async {
    final response = await _dio.post('/warehouses/', data: {'name': name, 'code': code});
    return Warehouse.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<StockItem>> fetchStockItems({bool lowStockOnly = false}) async {
    final response = await _dio.get(lowStockOnly ? '/stock-items/low_stock/' : '/stock-items/');
    final results = response.data['results'] as List;
    return results.map((e) => StockItem.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<StockMovement>> fetchMovements() async {
    final response = await _dio.get('/stock-movements/');
    final results = response.data['results'] as List;
    return results.map((e) => StockMovement.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> stockIn({
    required String warehouseId,
    required String productId,
    required double quantity,
    required double unitCost,
    String reference = '',
    String reason = '',
    String? batchNumber,
    String? expiryDate,
    List<String>? serialNumbers,
  }) {
    return _dio.post('/inventory/stock-in/', data: {
      'warehouse': warehouseId,
      'product': productId,
      'quantity': quantity,
      'unit_cost': unitCost,
      'reference': reference,
      'reason': reason,
      if (batchNumber != null && batchNumber.isNotEmpty) 'batch_number': batchNumber,
      if (expiryDate != null) 'expiry_date': expiryDate,
      if (serialNumbers != null && serialNumbers.isNotEmpty) 'serial_numbers': serialNumbers,
    });
  }

  Future<void> stockOut({
    required String warehouseId,
    required String productId,
    required double quantity,
    String reference = '',
    String reason = '',
  }) {
    return _dio.post('/inventory/stock-out/', data: {
      'warehouse': warehouseId,
      'product': productId,
      'quantity': quantity,
      'reference': reference,
      'reason': reason,
    });
  }

  Future<void> transferStock({
    required String fromWarehouseId,
    required String toWarehouseId,
    required String productId,
    required double quantity,
    String reference = '',
    String reason = '',
  }) {
    return _dio.post('/inventory/stock-transfer/', data: {
      'from_warehouse': fromWarehouseId,
      'to_warehouse': toWarehouseId,
      'product': productId,
      'quantity': quantity,
      'reference': reference,
      'reason': reason,
    });
  }

  Future<void> adjustStock({
    required String warehouseId,
    required String productId,
    required double quantityDelta,
    String reason = '',
    String? batchNumber,
    String? expiryDate,
    List<String>? serialNumbers,
  }) {
    return _dio.post('/inventory/stock-adjustment/', data: {
      'warehouse': warehouseId,
      'product': productId,
      'quantity_delta': quantityDelta,
      'reason': reason,
      if (batchNumber != null && batchNumber.isNotEmpty) 'batch_number': batchNumber,
      if (expiryDate != null) 'expiry_date': expiryDate,
      if (serialNumbers != null && serialNumbers.isNotEmpty) 'serial_numbers': serialNumbers,
    });
  }
}
