import 'package:dio/dio.dart';

import '../domain/customer.dart';

class CustomerRepository {
  CustomerRepository(this._dio);
  final Dio _dio;

  Future<List<Customer>> fetchCustomers({String? search}) async {
    final response = await _dio.get('/customers/', queryParameters: {
      if (search != null && search.isNotEmpty) 'search': search,
    });
    final results = response.data['results'] as List;
    return results.map((e) => Customer.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Customer> createCustomer({
    required String name,
    String phone = '',
    String email = '',
    double creditLimit = 0,
  }) async {
    final response = await _dio.post('/customers/', data: {
      'name': name,
      'phone': phone,
      'email': email,
      'credit_limit': creditLimit,
    });
    return Customer.fromJson(response.data as Map<String, dynamic>);
  }
}
