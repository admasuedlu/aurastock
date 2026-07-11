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

final purchaseSummaryProvider = FutureProvider.autoDispose<PurchaseSummary>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchPurchaseSummary();
});

final topProductsProvider = FutureProvider.autoDispose<List<TopProductRow>>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchTopProducts();
});

final abcAnalysisProvider = FutureProvider.autoDispose<AbcAnalysis>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchAbcAnalysis();
});

final inventoryValuationProvider = FutureProvider.autoDispose<InventoryValuation>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchInventoryValuation();
});

final deadStockProvider = FutureProvider.autoDispose<List<DeadStockRow>>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchDeadStock();
});

final expiringBatchesProvider = FutureProvider.autoDispose<List<ExpiringBatchRow>>((ref) {
  return ref.watch(reportsRepositoryProvider).fetchExpiringBatches();
});
