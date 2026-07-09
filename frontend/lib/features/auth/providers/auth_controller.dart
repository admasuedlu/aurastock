import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../domain/user.dart';

class AuthController extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() async {
    final tokenStorage = ref.read(tokenStorageProvider);
    final token = await tokenStorage.accessToken;
    if (token == null) return null;
    try {
      return await ref.read(authRepositoryProvider).fetchMe();
    } catch (_) {
      await tokenStorage.clear();
      return null;
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).login(email: email, password: password),
    );
  }

  Future<void> signup({
    required String companyName,
    required String ownerFirstName,
    required String ownerLastName,
    required String ownerEmail,
    required String ownerPhone,
    required String password,
  }) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).signup(
            companyName: companyName,
            ownerFirstName: ownerFirstName,
            ownerLastName: ownerLastName,
            ownerEmail: ownerEmail,
            ownerPhone: ownerPhone,
            password: password,
          ),
    );
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    state = const AsyncData(null);
  }

  /// Called by the API client when a refresh-token cycle fails, so the
  /// session is dropped even outside a user-initiated logout tap.
  Future<void> forceLogout() async {
    await ref.read(tokenStorageProvider).clear();
    state = const AsyncData(null);
  }
}

final authControllerProvider = AsyncNotifierProvider<AuthController, AppUser?>(AuthController.new);
