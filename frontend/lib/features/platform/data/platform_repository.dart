import 'package:dio/dio.dart';

import '../domain/platform_models.dart';

class PlatformRepository {
  PlatformRepository(this._dio);
  final Dio _dio;

  Future<PlatformOverview> fetchOverview() async {
    final response = await _dio.get('/platform/overview/');
    return PlatformOverview.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<TenantCompany>> fetchCompanies({String? search}) async {
    final response = await _dio.get('/platform/companies/', queryParameters: {
      'page_size': 100,
      if (search != null && search.isNotEmpty) 'search': search,
    });
    final results = response.data['results'] as List;
    return results.map((e) => TenantCompany.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> suspendCompany(String id) => _dio.post('/platform/companies/$id/suspend/');

  Future<void> activateCompany(String id) => _dio.post('/platform/companies/$id/activate/');

  Future<void> changePlan(String companyId, String planId) =>
      _dio.post('/platform/companies/$companyId/change-plan/', data: {'plan': planId});

  Future<List<SaasPlan>> fetchPlans() async {
    final response = await _dio.get('/platform/plans/', queryParameters: {'page_size': 100});
    final results = response.data['results'] as List;
    return results.map((e) => SaasPlan.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> savePlan({
    String? id,
    required String name,
    required String code,
    required String priceMonthlyEtb,
    required int maxUsers,
    required int maxBranches,
    required int maxWarehouses,
  }) {
    final body = {
      'name': name,
      'code': code,
      'price_monthly_etb': priceMonthlyEtb,
      'max_users': maxUsers,
      'max_branches': maxBranches,
      'max_warehouses': maxWarehouses,
    };
    return id == null
        ? _dio.post('/platform/plans/', data: body)
        : _dio.patch('/platform/plans/$id/', data: body);
  }
}
