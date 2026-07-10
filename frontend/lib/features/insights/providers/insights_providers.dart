import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/insights_repository.dart';
import '../domain/insight_models.dart';

final insightsRepositoryProvider = Provider<InsightsRepository>((ref) {
  return InsightsRepository(ref.watch(apiClientProvider).dio);
});

final reorderSuggestionsProvider = FutureProvider.autoDispose<List<ReorderSuggestion>>((ref) {
  return ref.watch(insightsRepositoryProvider).fetchReorderSuggestions();
});

final anomaliesProvider = FutureProvider.autoDispose<List<AnomalyRow>>((ref) {
  return ref.watch(insightsRepositoryProvider).fetchAnomalies();
});

final selectedForecastProductProvider = StateProvider<String?>((ref) => null);

final demandForecastProvider = FutureProvider.autoDispose<DemandForecast?>((ref) async {
  final productId = ref.watch(selectedForecastProductProvider);
  if (productId == null) return null;
  return ref.watch(insightsRepositoryProvider).fetchDemandForecast(productId);
});
