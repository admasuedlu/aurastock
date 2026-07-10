import 'package:dio/dio.dart';

/// Staff-side management of a customer's/supplier's portal login. Uses the
/// normal staff (JWT) Dio -- these are `/customers/{id}/portal-access/` and
/// `/suppliers/{id}/portal-access/` actions, scoped to the staff member's own
/// tenant by the backend.
class PortalAccessRepository {
  PortalAccessRepository(this._dio);
  final Dio _dio;

  /// [resource] is "customers" or "suppliers".
  Future<PortalAccessStatus> fetch(String resource, String id) async {
    final response = await _dio.get('/$resource/$id/portal-access/');
    return PortalAccessStatus.fromJson(response.data as Map<String, dynamic>);
  }

  Future<PortalAccessStatus> grant(String resource, String id,
      {required String email, required String password}) async {
    final response = await _dio.post('/$resource/$id/portal-access/', data: {
      'email': email,
      'password': password,
    });
    return PortalAccessStatus.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> revoke(String resource, String id) async {
    await _dio.delete('/$resource/$id/portal-access/');
  }
}

class PortalAccessStatus {
  const PortalAccessStatus({required this.hasAccess, this.email, this.lastLoginAt});

  factory PortalAccessStatus.fromJson(Map<String, dynamic> json) {
    return PortalAccessStatus(
      hasAccess: json['has_access'] as bool? ?? false,
      email: json['email'] as String?,
      lastLoginAt: json['last_login_at'] as String?,
    );
  }

  final bool hasAccess;
  final String? email;
  final String? lastLoginAt;
}
