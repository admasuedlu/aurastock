import 'package:dio/dio.dart';

import '../domain/insight_models.dart';

class InsightsRepository {
  InsightsRepository(this._dio);
  final Dio _dio;

  Future<List<ReorderSuggestion>> fetchReorderSuggestions() async {
    final response = await _dio.get('/insights/reorder-suggestions/');
    final rows = response.data['rows'] as List;
    return rows.map((e) => ReorderSuggestion.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<DemandForecast> fetchDemandForecast(String productId, {int days = 14}) async {
    final response = await _dio.get('/insights/demand-forecast/', queryParameters: {
      'product': productId,
      'days': days,
    });
    return DemandForecast.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<AnomalyRow>> fetchAnomalies({int days = 7}) async {
    final response = await _dio.get('/insights/anomalies/', queryParameters: {'days': days});
    final rows = response.data['rows'] as List;
    return rows.map((e) => AnomalyRow.fromJson(e as Map<String, dynamic>)).toList();
  }
}
