import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../../core/config/env.dart';
import '../../../core/providers/core_providers.dart';
import '../data/notifications_repository.dart';
import '../domain/notification_models.dart';

final notificationsRepositoryProvider = Provider<NotificationsRepository>((ref) {
  return NotificationsRepository(ref.watch(apiClientProvider).dio);
});

final notificationsControllerProvider =
    StateNotifierProvider<NotificationsController, AsyncValue<List<AppNotification>>>((ref) {
  return NotificationsController(ref);
});

final unreadNotificationCountProvider = Provider<int>((ref) {
  final notifications = ref.watch(notificationsControllerProvider).valueOrNull ?? const [];
  return notifications.where((n) => !n.isRead).length;
});

class NotificationsController extends StateNotifier<AsyncValue<List<AppNotification>>> {
  NotificationsController(this._ref) : super(const AsyncValue.loading()) {
    _load();
    _connect();
  }

  final Ref _ref;
  WebSocketChannel? _channel;

  NotificationsRepository get _repo => _ref.read(notificationsRepositoryProvider);

  Future<void> _load() async {
    try {
      final notifications = await _repo.fetchNotifications();
      state = AsyncValue.data(notifications);
    } catch (error, stack) {
      state = AsyncValue.error(error, stack);
    }
  }

  Future<void> _connect() async {
    final token = await _ref.read(tokenStorageProvider).accessToken;
    if (token == null) return;
    try {
      final channel = WebSocketChannel.connect(
        Uri.parse('${Env.wsBaseUrl}/ws/notifications/?token=$token'),
      );
      _channel = channel;
      channel.stream.listen(
        (raw) {
          final json = jsonDecode(raw as String) as Map<String, dynamic>;
          final incoming = AppNotification.fromJson(json);
          final current = state.valueOrNull ?? const [];
          if (current.any((n) => n.id == incoming.id)) return;
          state = AsyncValue.data([incoming, ...current]);
        },
        // A dropped socket just means the badge stops live-updating; the
        // list is still correct on next manual refresh, so fail quietly.
        onError: (_) {},
        cancelOnError: true,
      );
    } catch (_) {
      // No live push available (offline, dev server not running channels, etc).
    }
  }

  Future<void> markRead(String id) async {
    final current = state.valueOrNull;
    if (current == null) return;
    state = AsyncValue.data([for (final n in current) n.id == id ? n.copyWith(isRead: true) : n]);
    try {
      await _repo.markRead(id);
    } catch (_) {
      await _load();
    }
  }

  Future<void> markAllRead() async {
    final current = state.valueOrNull;
    if (current == null) return;
    state = AsyncValue.data([for (final n in current) n.copyWith(isRead: true)]);
    try {
      await _repo.markAllRead();
    } catch (_) {
      await _load();
    }
  }

  Future<void> refresh() => _load();

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }
}
