import 'package:dio/dio.dart';

import '../domain/report_models.dart';

class ReportsRepository {
  ReportsRepository(this._dio);
  final Dio _dio;

  Future<SalesSummary> fetchSalesSummary({int days = 30}) async {
    final response = await _dio.get('/reports/sales-summary/', queryParameters: {'days': days});
    return SalesSummary.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PurchaseSummary> fetchPurchaseSummary({int days = 30}) async {
    final response = await _dio.get('/reports/purchase-summary/', queryParameters: {'days': days});
    return PurchaseSummary.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<TopProductRow>> fetchTopProducts({int limit = 10}) async {
    final response = await _dio.get('/reports/top-products/', queryParameters: {'limit': limit});
    final rows = response.data['rows'] as List;
    return rows.map((e) => TopProductRow.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<AbcAnalysis> fetchAbcAnalysis() async {
    final response = await _dio.get('/reports/abc-analysis/');
    return AbcAnalysis.fromJson(response.data as Map<String, dynamic>);
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

  /// Batches on hand within [days] of expiry (or already expired), soonest
  /// first. Served by the inventory app's /batches/expiring/ endpoint.
  Future<List<ExpiringBatchRow>> fetchExpiringBatches({int days = 30}) async {
    final response = await _dio.get('/batches/expiring/', queryParameters: {'days': days});
    final results = response.data['results'] as List;
    return results.map((e) => ExpiringBatchRow.fromJson(e as Map<String, dynamic>)).toList();
  }
}
