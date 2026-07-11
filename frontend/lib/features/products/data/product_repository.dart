import 'package:dio/dio.dart';

import '../domain/product.dart';

class ProductRepository {
  ProductRepository(this._dio);
  final Dio _dio;

  Future<List<Product>> fetchProducts({String? search}) async {
    final response = await _dio.get('/products/', queryParameters: {
      if (search != null && search.isNotEmpty) 'search': search,
    });
    final results = response.data['results'] as List;
    return results.map((e) => Product.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Category>> fetchCategories() async {
    final response = await _dio.get('/categories/');
    final results = response.data['results'] as List;
    return results.map((e) => Category.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<UnitOfMeasure>> fetchUnits() async {
    final response = await _dio.get('/units/');
    final results = response.data['results'] as List;
    return results.map((e) => UnitOfMeasure.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Product> createProduct({
    required String name,
    String? categoryId,
    required String unitId,
    required double costPrice,
    required double sellingPrice,
    required double reorderLevel,
    bool trackBatch = false,
    bool trackExpiry = false,
  }) async {
    final response = await _dio.post('/products/', data: {
      'name': name,
      if (categoryId != null) 'category': categoryId,
      'unit': unitId,
      'cost_price': costPrice,
      'selling_price': sellingPrice,
      'reorder_level': reorderLevel,
      'track_batch': trackBatch,
      'track_expiry': trackExpiry,
    });
    return Product.fromJson(response.data as Map<String, dynamic>);
  }
}
