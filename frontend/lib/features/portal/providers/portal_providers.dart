import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/env.dart';
import '../../../core/providers/core_providers.dart';
import '../data/portal_access_repository.dart';
import '../data/portal_repository.dart';
import '../data/portal_session_storage.dart';
import '../domain/portal_models.dart';

final portalSessionStorageProvider = Provider<PortalSessionStorage>((ref) => PortalSessionStorage());

/// Staff-side portal-access management runs on the normal JWT Dio.
final portalAccessRepositoryProvider = Provider<PortalAccessRepository>((ref) {
  return PortalAccessRepository(ref.watch(apiClientProvider).dio);
});

/// A Dio dedicated to the portal. It attaches `Authorization: Portal <token>`
/// (never a Bearer JWT) and, when the token is rejected as expired/invalid,
/// drops the portal session so the router sends the user back to login.
final portalDioProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: Env.apiBaseUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 15),
  ));
  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) {
      final token = ref.read(portalSessionControllerProvider).valueOrNull?.token;
      if (token != null) {
        options.headers['Authorization'] = 'Portal $token';
      }
      handler.next(options);
    },
    onError: (err, handler) {
      final code = err.response?.statusCode;
      final isLogin = err.requestOptions.path.endsWith('/portal/login/');
      // 401/403 on a non-login portal call means the token is no longer good.
      if (!isLogin && (code == 401 || code == 403)) {
        ref.read(portalSessionControllerProvider.notifier).forceLogout();
      }
      handler.next(err);
    },
  ));
  return dio;
});

final portalRepositoryProvider = Provider<PortalRepository>((ref) {
  return PortalRepository(ref.watch(portalDioProvider));
});

class PortalSessionController extends AsyncNotifier<PortalSession?> {
  @override
  Future<PortalSession?> build() async {
    return ref.read(portalSessionStorageProvider).read();
  }

  Future<void> login(String email, String password) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final session = await ref.read(portalRepositoryProvider).login(email: email, password: password);
      await ref.read(portalSessionStorageProvider).save(session);
      return session;
    });
  }

  Future<void> logout() async {
    await ref.read(portalSessionStorageProvider).clear();
    state = const AsyncData(null);
  }

  /// Fire-and-forget drop used by the Dio interceptor on an expired token;
  /// unlike [logout] it can't be awaited from inside an error handler.
  void forceLogout() {
    ref.read(portalSessionStorageProvider).clear();
    state = const AsyncData(null);
  }
}

final portalSessionControllerProvider =
    AsyncNotifierProvider<PortalSessionController, PortalSession?>(PortalSessionController.new);

final portalQuotationsProvider = FutureProvider.autoDispose<List<PortalDocument>>((ref) {
  return ref.watch(portalRepositoryProvider).fetchQuotations();
});

final portalSalesOrdersProvider = FutureProvider.autoDispose<List<PortalDocument>>((ref) {
  return ref.watch(portalRepositoryProvider).fetchSalesOrders();
});

final portalInvoicesProvider = FutureProvider.autoDispose<List<PortalDocument>>((ref) {
  return ref.watch(portalRepositoryProvider).fetchInvoices();
});

final portalPurchaseOrdersProvider = FutureProvider.autoDispose<List<PortalDocument>>((ref) {
  return ref.watch(portalRepositoryProvider).fetchPurchaseOrders();
});
