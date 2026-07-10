import 'package:dio/dio.dart';

import '../domain/report_models.dart';

class ReportsRepository {
  ReportsRepository(this._dio);
  final Dio _dio;

  Future<SalesSummary> fetchSalesSummary({int days = 30}) async {
    final response = await _dio.get('/reports/sales-summary/', queryParameters: {'days': days});
    return SalesSummary.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<TopProductRow>> fetchTopProducts({int limit = 10}) async {
    final response = await _dio.get('/reports/top-products/', queryParameters: {'limit': limit});
    final rows = response.data['rows'] as List;
    return rows.map((e) => TopProductRow.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<InventoryValuation> fetchInventoryValuation() async {
    final response = await _dio.get('/reports/inventory-valuation/');
    return InventoryValuation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<DeadStockRow>> fetchDeadStock({int days = 30}) async {
    final response = await _dio.get('/reports/dead-stock/', queryParameters: {'days': days});
    final rows = response.data['rows'] as List;
    return rows.map((e) => DeadStockRow.fromJson(e as Map<String, dynamic>)).toList();
  }
}
