import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/supplier_repository.dart';
import '../domain/supplier.dart';

final supplierRepositoryProvider = Provider<SupplierRepository>((ref) {
  return SupplierRepository(ref.watch(apiClientProvider).dio);
});

final supplierSearchProvider = StateProvider<String>((ref) => '');

final supplierListProvider = FutureProvider.autoDispose<List<Supplier>>((ref) {
  final search = ref.watch(supplierSearchProvider);
  return ref.watch(supplierRepositoryProvider).fetchSuppliers(search: search);
});
