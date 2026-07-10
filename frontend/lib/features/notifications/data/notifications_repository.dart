import 'package:dio/dio.dart';

import '../domain/notification_models.dart';

class NotificationsRepository {
  NotificationsRepository(this._dio);
  final Dio _dio;

  Future<List<AppNotification>> fetchNotifications() async {
    final response = await _dio.get('/notifications/', queryParameters: {'page_size': 50});
    final results = response.data['results'] as List;
    return results.map((e) => AppNotification.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<int> fetchUnreadCount() async {
    final response = await _dio.get('/notifications/unread_count/');
    return response.data['count'] as int;
  }

  Future<void> markRead(String id) => _dio.post('/notifications/$id/mark_read/');

  Future<void> markAllRead() => _dio.post('/notifications/mark_all_read/');
}
