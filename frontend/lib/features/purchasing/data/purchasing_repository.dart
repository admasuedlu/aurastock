import 'package:dio/dio.dart';

import '../../../core/widgets/line_item_editor.dart';
import '../domain/purchasing_models.dart';

class PurchasingRepository {
  PurchasingRepository(this._dio);
  final Dio _dio;

  Future<List<PurchaseOrder>> fetchPurchaseOrders() async {
    final response = await _dio.get('/purchase-orders/');
    final results = response.data['results'] as List;
    return results.map((e) => PurchaseOrder.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<PurchaseOrder> createPurchaseOrder({
    required String supplierId,
    required List<LineItemDraft> items,
  }) async {
    final response = await _dio.post('/purchase-orders/', data: {
      'supplier': supplierId,
      'items': items
          .where((i) => i.isValid)
          .map((i) => {'product': i.productId, 'quantity': i.quantity, 'unit_price': i.unitPrice})
          .toList(),
    });
    return PurchaseOrder.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PurchaseOrder> sendPurchaseOrder(String purchaseOrderId) async {
    final response = await _dio.post('/purchase-orders/$purchaseOrderId/send/');
    return PurchaseOrder.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> receiveGoods({
    required String purchaseOrderId,
    required String warehouseId,
    required List<Map<String, dynamic>> items,
  }) async {
    await _dio.post('/goods-receipts/', data: {
      'purchase_order': purchaseOrderId,
      'warehouse': warehouseId,
      'items': items,
    });
  }

  Future<PurchaseOrder> recordPayment(String purchaseOrderId, {required double amount, required String method}) async {
    final response = await _dio.post('/purchase-orders/$purchaseOrderId/record-payment/', data: {
      'amount': amount,
      'method': method,
    });
    return PurchaseOrder.fromJson(response.data as Map<String, dynamic>);
  }
}
