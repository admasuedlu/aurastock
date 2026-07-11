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
    String barcode = '',
    bool trackBatch = false,
    bool trackExpiry = false,
    bool isBundle = false,
  }) async {
    final response = await _dio.post('/products/', data: {
      'name': name,
      if (categoryId != null) 'category': categoryId,
      'unit': unitId,
      'cost_price': costPrice,
      'selling_price': sellingPrice,
      'reorder_level': reorderLevel,
      if (barcode.isNotEmpty) 'barcode': barcode,
      'track_batch': trackBatch,
      'track_expiry': trackExpiry,
      if (isBundle) 'product_type': 'bundle',
    });
    return Product.fromJson(response.data as Map<String, dynamic>);
  }

  /// Resolve a scanned barcode to a product (exact match on the product or a
  /// variant barcode). Returns null when nothing matches (the endpoint 404s).
  Future<Product?> lookupByBarcode(String code) async {
    try {
      final response = await _dio.get('/products/lookup/', queryParameters: {'barcode': code});
      return Product.fromJson(response.data['product'] as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<List<BundleComponent>> fetchBundleComponents(String bundleId) async {
    final response = await _dio.get('/bundle-components/', queryParameters: {'bundle': bundleId});
    final results = response.data['results'] as List;
    return results.map((e) => BundleComponent.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> addBundleComponent(String bundleId, String componentId, double quantity) {
    return _dio.post('/bundle-components/', data: {
      'bundle': bundleId,
      'component': componentId,
      'quantity': quantity,
    });
  }

  Future<void> removeBundleComponent(String id) {
    return _dio.delete('/bundle-components/$id/');
  }

  Future<void> assembleBundle({
    required String warehouseId,
    required String bundleId,
    required double quantity,
  }) {
    return _dio.post('/inventory/assemble/', data: {
      'warehouse': warehouseId,
      'bundle_product': bundleId,
      'quantity': quantity,
    });
  }
}
