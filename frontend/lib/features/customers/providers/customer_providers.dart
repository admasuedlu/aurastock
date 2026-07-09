import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/customer_repository.dart';
import '../domain/customer.dart';

final customerRepositoryProvider = Provider<CustomerRepository>((ref) {
  return CustomerRepository(ref.watch(apiClientProvider).dio);
});

final customerSearchProvider = StateProvider<String>((ref) => '');

final customerListProvider = FutureProvider.autoDispose<List<Customer>>((ref) {
  final search = ref.watch(customerSearchProvider);
  return ref.watch(customerRepositoryProvider).fetchCustomers(search: search);
});
