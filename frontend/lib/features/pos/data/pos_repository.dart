import 'package:dio/dio.dart';

import '../domain/pos_models.dart';

class PosRepository {
  PosRepository(this._dio);
  final Dio _dio;

  Future<PosSession?> fetchCurrentSession() async {
    final response = await _dio.get('/pos-sessions/current/');
    if (response.data == null) return null;
    return PosSession.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PosSession> openSession({required String warehouseId, required double openingCash}) async {
    final response = await _dio.post('/pos-sessions/', data: {
      'warehouse': warehouseId,
      'opening_cash': openingCash,
    });
    return PosSession.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PosSession> closeSession(String sessionId, {required double closingCash}) async {
    final response = await _dio.post('/pos-sessions/$sessionId/close/', data: {
      'closing_cash': closingCash,
    });
    return PosSession.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<PosTransaction>> fetchTransactions(String sessionId) async {
    final response = await _dio.get('/pos-transactions/', queryParameters: {'session': sessionId});
    final results = response.data['results'] as List;
    return results.map((e) => PosTransaction.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<PosTransaction> createTransaction({
    required String sessionId,
    String? customerId,
    required String paymentMethod,
    required double amountTendered,
    required List<Map<String, dynamic>> items,
  }) async {
    final response = await _dio.post('/pos-transactions/', data: {
      'session': sessionId,
      'customer': ?customerId,
      'payment_method': paymentMethod,
      'amount_tendered': amountTendered,
      'items': items,
    });
    return PosTransaction.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PosTransaction> refundTransaction(String transactionId) async {
    final response = await _dio.post('/pos-transactions/$transactionId/refund/');
    return PosTransaction.fromJson(response.data as Map<String, dynamic>);
  }
}
