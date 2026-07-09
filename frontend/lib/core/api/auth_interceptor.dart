import 'package:dio/dio.dart';

import '../config/env.dart';
import '../storage/token_storage.dart';

/// Attaches the access token to every request and transparently refreshes
/// it on a 401 (retrying the original request once). Falls back to
/// [onSessionExpired] when the refresh token itself is no longer valid.
class AuthInterceptor extends Interceptor {
  AuthInterceptor(this._tokenStorage, this._dio, {required this.onSessionExpired});

  final TokenStorage _tokenStorage;
  final Dio _dio;
  final Future<void> Function() onSessionExpired;

  bool _isRefreshing = false;

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _tokenStorage.accessToken;
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final isUnauthorized = err.response?.statusCode == 401;
    final isRetry = err.requestOptions.extra['retried'] == true;

    if (!isUnauthorized || isRetry || _isRefreshing) {
      handler.next(err);
      return;
    }

    _isRefreshing = true;
    try {
      final refreshToken = await _tokenStorage.refreshToken;
      if (refreshToken == null) {
        await onSessionExpired();
        handler.next(err);
        return;
      }

      final refreshDio = Dio(BaseOptions(baseUrl: Env.apiBaseUrl));
      final response = await refreshDio.post(
        '/auth/token/refresh/',
        data: {'refresh': refreshToken},
      );
      final newAccess = response.data['access'] as String;
      await _tokenStorage.updateAccessToken(newAccess);

      final retryOptions = err.requestOptions;
      retryOptions.headers['Authorization'] = 'Bearer $newAccess';
      retryOptions.extra['retried'] = true;
      final retryResponse = await _dio.fetch(retryOptions);
      handler.resolve(retryResponse);
    } catch (_) {
      await onSessionExpired();
      handler.next(err);
    } finally {
      _isRefreshing = false;
    }
  }
}
