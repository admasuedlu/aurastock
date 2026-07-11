import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/purchasing_repository.dart';
import '../domain/purchasing_models.dart';

final purchasingRepositoryProvider = Provider<PurchasingRepository>((ref) {
  return PurchasingRepository(ref.watch(apiClientProvider).dio);
});

final purchaseOrderListProvider = FutureProvider.autoDispose<List<PurchaseOrder>>((ref) {
  return ref.watch(purchasingRepositoryProvider).fetchPurchaseOrders();
});

final purchaseRequestListProvider = FutureProvider.autoDispose<List<PurchaseRequest>>((ref) {
  return ref.watch(purchasingRepositoryProvider).fetchPurchaseRequests();
});
