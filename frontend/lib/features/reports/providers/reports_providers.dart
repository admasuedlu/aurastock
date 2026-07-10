import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/reports_repository.dart';
import '../domain/report_models.dart';

final reportsRepositoryProvider = Provider<ReportsRepository>((ref) {
  return ReportsRepository(ref.watch(apiClientProvider).dio);
});

final salesSummaryProvider = FutureProvider.autoDispose<SalesSummary>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchSalesSummary();
});

final topProductsProvider = FutureProvider.autoDispose<List<TopProductRow>>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchTopProducts();
});

final inventoryValuationProvider = FutureProvider.autoDispose<InventoryValuation>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchInventoryValuation();
});

final deadStockProvider = FutureProvider.autoDispose<List<DeadStockRow>>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchDeadStock();
});
