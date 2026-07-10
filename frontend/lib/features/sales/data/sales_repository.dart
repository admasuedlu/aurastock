import 'package:dio/dio.dart';

import '../../../core/widgets/line_item_editor.dart';
import '../domain/sales_models.dart';

class SalesRepository {
  SalesRepository(this._dio);
  final Dio _dio;

  Future<List<Quotation>> fetchQuotations() async {
    final response = await _dio.get('/quotations/');
    final results = response.data['results'] as List;
    return results.map((e) => Quotation.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Quotation> createQuotation({required String customerId, required List<LineItemDraft> items}) async {
    final response = await _dio.post('/quotations/', data: {
      'customer': customerId,
      'items': _itemPayload(items),
    });
    return Quotation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Quotation> sendQuotation(String quotationId) async {
    final response = await _dio.post('/quotations/$quotationId/send/');
    return Quotation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<SalesOrder> convertQuotationToOrder(String quotationId) async {
    final response = await _dio.post('/quotations/$quotationId/convert-to-order/');
    return SalesOrder.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<SalesOrder>> fetchSalesOrders() async {
    final response = await _dio.get('/sales-orders/');
    final results = response.data['results'] as List;
    return results.map((e) => SalesOrder.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Invoice>> fetchInvoices() async {
    final response = await _dio.get('/invoices/');
    final results = response.data['results'] as List;
    return results.map((e) => Invoice.fromJson(e as Map<String, dynamic>)).toList();
  }

  List<Map<String, dynamic>> _itemPayload(List<LineItemDraft> items) {
    return items
        .where((i) => i.isValid)
        .map((i) => {
              'product': i.productId,
              'quantity': i.quantity,
              'unit_price': i.unitPrice,
            })
        .toList();
  }

  Future<SalesOrder> createSalesOrder({required String customerId, required List<LineItemDraft> items}) async {
    final response = await _dio.post('/sales-orders/', data: {
      'customer': customerId,
      'items': _itemPayload(items),
    });
    return SalesOrder.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Invoice> createInvoice({
    required String customerId,
    required String warehouseId,
    required List<LineItemDraft> items,
  }) async {
    final response = await _dio.post('/invoices/', data: {
      'customer': customerId,
      'warehouse': warehouseId,
      'items': _itemPayload(items),
    });
    return Invoice.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Invoice> confirmInvoice(String invoiceId) async {
    final response = await _dio.post('/invoices/$invoiceId/confirm/');
    return Invoice.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Invoice> recordPayment(String invoiceId, {required double amount, required String method}) async {
    final response = await _dio.post('/invoices/$invoiceId/record-payment/', data: {
      'amount': amount,
      'method': method,
    });
    return Invoice.fromJson(response.data as Map<String, dynamic>);
  }
}
