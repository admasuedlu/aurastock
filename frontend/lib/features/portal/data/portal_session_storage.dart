import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../domain/portal_models.dart';

/// Persists the portal session separately from the staff JWT so the two
/// login modes never collide (a device could, in principle, have both).
class PortalSessionStorage {
  PortalSessionStorage() : _storage = const FlutterSecureStorage();

  final FlutterSecureStorage _storage;
  static const _key = 'portal_session';

  Future<void> save(PortalSession session) =>
      _storage.write(key: _key, value: jsonEncode(session.toJson()));

  Future<PortalSession?> read() async {
    final raw = await _storage.read(key: _key);
    if (raw == null) return null;
    try {
      return PortalSession.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<void> clear() => _storage.delete(key: _key);
}
