import 'package:dio/dio.dart';

import '../../../core/storage/token_storage.dart';
import '../domain/user.dart';

class AuthRepository {
  AuthRepository(this._dio, this._tokenStorage);

  final Dio _dio;
  final TokenStorage _tokenStorage;

  Future<AppUser> login({required String email, required String password}) async {
    final response = await _dio.post('/auth/token/', data: {
      'email': email,
      'password': password,
    });
    await _tokenStorage.saveTokens(
      access: response.data['access'] as String,
      refresh: response.data['refresh'] as String,
    );
    return fetchMe();
  }

  Future<AppUser> signup({
    required String companyName,
    required String ownerFirstName,
    required String ownerLastName,
    required String ownerEmail,
    required String ownerPhone,
    required String password,
  }) async {
    final response = await _dio.post('/auth/signup/', data: {
      'company_name': companyName,
      'owner_first_name': ownerFirstName,
      'owner_last_name': ownerLastName,
      'owner_email': ownerEmail,
      'owner_phone': ownerPhone,
      'password': password,
    });
    await _tokenStorage.saveTokens(
      access: response.data['access'] as String,
      refresh: response.data['refresh'] as String,
    );
    return AppUser.fromJson(response.data['user'] as Map<String, dynamic>);
  }

  Future<AppUser> fetchMe() async {
    final response = await _dio.get('/auth/me/');
    return AppUser.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> logout() => _tokenStorage.clear();
}
