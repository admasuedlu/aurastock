import 'package:dio/dio.dart';

import '../domain/supplier.dart';

class SupplierRepository {
  SupplierRepository(this._dio);
  final Dio _dio;

  Future<List<Supplier>> fetchSuppliers({String? search}) async {
    final response = await _dio.get('/suppliers/', queryParameters: {
      if (search != null && search.isNotEmpty) 'search': search,
    });
    final results = response.data['results'] as List;
    return results.map((e) => Supplier.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Supplier> createSupplier({
    required String name,
    String phone = '',
    String email = '',
    int paymentTermsDays = 30,
  }) async {
    final response = await _dio.post('/suppliers/', data: {
      'name': name,
      'phone': phone,
      'email': email,
      'payment_terms_days': paymentTermsDays,
    });
    return Supplier.fromJson(response.data as Map<String, dynamic>);
  }
}
