import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/sales_repository.dart';
import '../domain/sales_models.dart';

final salesRepositoryProvider = Provider<SalesRepository>((ref) {
  return SalesRepository(ref.watch(apiClientProvider).dio);
});

final salesOrderListProvider = FutureProvider.autoDispose<List<SalesOrder>>((ref) {
  return ref.watch(salesRepositoryProvider).fetchSalesOrders();
});

final invoiceListProvider = FutureProvider.autoDispose<List<Invoice>>((ref) {
  return ref.watch(salesRepositoryProvider).fetchInvoices();
});
