import 'package:dio/dio.dart';

import '../config/env.dart';
import '../storage/token_storage.dart';
import 'auth_interceptor.dart';

class ApiClient {
  ApiClient(TokenStorage tokenStorage, {required Future<void> Function() onSessionExpired})
      : dio = Dio(BaseOptions(
          baseUrl: Env.apiBaseUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        )) {
    dio.interceptors.add(AuthInterceptor(tokenStorage, dio, onSessionExpired: onSessionExpired));
  }

  final Dio dio;
}
