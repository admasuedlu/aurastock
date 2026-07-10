import 'package:dio/dio.dart';

import '../domain/portal_models.dart';

class PortalRepository {
  PortalRepository(this._dio);
  final Dio _dio;

  Future<PortalSession> login({required String email, required String password}) async {
    final response = await _dio.post('/portal/login/', data: {
      'email': email,
      'password': password,
    });
    return PortalSession.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<PortalDocument>> _fetchList(String path) async {
    final response = await _dio.get(path);
    final results = response.data['results'] as List;
    return results.map((e) => PortalDocument.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<PortalDocument>> fetchQuotations() => _fetchList('/portal/quotations/');
  Future<List<PortalDocument>> fetchSalesOrders() => _fetchList('/portal/sales-orders/');
  Future<List<PortalDocument>> fetchInvoices() => _fetchList('/portal/invoices/');
  Future<List<PortalDocument>> fetchPurchaseOrders() => _fetchList('/portal/purchase-orders/');

  Future<PortalDocument> acceptQuotation(String id) => _act('/portal/quotations/$id/accept/');
  Future<PortalDocument> rejectQuotation(String id) => _act('/portal/quotations/$id/reject/');
  Future<PortalDocument> acknowledgePurchaseOrder(String id) =>
      _act('/portal/purchase-orders/$id/acknowledge/');

  Future<PortalDocument> _act(String path) async {
    final response = await _dio.post(path);
    return PortalDocument.fromJson(response.data as Map<String, dynamic>);
  }
}
