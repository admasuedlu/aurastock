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

  Future<List<PurchaseRequest>> fetchPurchaseRequests() async {
    final response = await _dio.get('/purchase-requests/');
    final results = response.data['results'] as List;
    return results.map((e) => PurchaseRequest.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<PurchaseRequest> createPurchaseRequest({
    String? supplierId,
    required List<LineItemDraft> items,
  }) async {
    final response = await _dio.post('/purchase-requests/', data: {
      if (supplierId != null) 'supplier': supplierId,
      'items': items
          .where((i) => i.isValid)
          .map((i) => {'product': i.productId, 'quantity': i.quantity, 'unit_price': i.unitPrice})
          .toList(),
    });
    return PurchaseRequest.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PurchaseRequest> submitPurchaseRequest(String id) async {
    final response = await _dio.post('/purchase-requests/$id/submit/');
    return PurchaseRequest.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PurchaseRequest> approvePurchaseRequest(String id) async {
    final response = await _dio.post('/purchase-requests/$id/approve/');
    return PurchaseRequest.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PurchaseRequest> rejectPurchaseRequest(String id, {required String reason}) async {
    final response = await _dio.post('/purchase-requests/$id/reject/', data: {'reason': reason});
    return PurchaseRequest.fromJson(response.data as Map<String, dynamic>);
  }

  /// Converts an approved request to a PO. [supplierId] is required only when
  /// the request itself has no supplier set.
  Future<PurchaseOrder> convertRequestToPo(String id, {String? supplierId}) async {
    final response = await _dio.post('/purchase-requests/$id/convert-to-po/', data: {
      if (supplierId != null) 'supplier': supplierId,
    });
    return PurchaseOrder.fromJson(response.data as Map<String, dynamic>);
  }
}
