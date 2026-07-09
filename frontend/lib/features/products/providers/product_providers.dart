import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/product_repository.dart';
import '../domain/product.dart';

final productRepositoryProvider = Provider<ProductRepository>((ref) {
  return ProductRepository(ref.watch(apiClientProvider).dio);
});

final productSearchProvider = StateProvider<String>((ref) => '');

final productListProvider = FutureProvider.autoDispose<List<Product>>((ref) async {
  final search = ref.watch(productSearchProvider);
  return ref.watch(productRepositoryProvider).fetchProducts(search: search);
});

final categoryListProvider = FutureProvider.autoDispose<List<Category>>((ref) {
  return ref.watch(productRepositoryProvider).fetchCategories();
});

final unitListProvider = FutureProvider.autoDispose<List<UnitOfMeasure>>((ref) {
  return ref.watch(productRepositoryProvider).fetchUnits();
});
