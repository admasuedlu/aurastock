import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/platform_repository.dart';
import '../domain/platform_models.dart';

final platformRepositoryProvider = Provider<PlatformRepository>((ref) {
  return PlatformRepository(ref.watch(apiClientProvider).dio);
});

final platformOverviewProvider = FutureProvider.autoDispose<PlatformOverview>((ref) {
  return ref.watch(platformRepositoryProvider).fetchOverview();
});

final tenantSearchProvider = StateProvider<String>((ref) => '');

final tenantCompaniesProvider = FutureProvider.autoDispose<List<TenantCompany>>((ref) {
  final search = ref.watch(tenantSearchProvider);
  return ref.watch(platformRepositoryProvider).fetchCompanies(search: search);
});

final saasPlansProvider = FutureProvider.autoDispose<List<SaasPlan>>((ref) {
  return ref.watch(platformRepositoryProvider).fetchPlans();
});
