import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../domain/notification_models.dart';
import '../providers/notifications_providers.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  IconData _iconFor(AppNotificationType type) {
    switch (type) {
      case AppNotificationType.lowStock:
        return Icons.warning_amber_rounded;
      case AppNotificationType.overdueInvoice:
        return Icons.receipt_long;
      case AppNotificationType.system:
        return Icons.info_outline;
    }
  }

  Color _colorFor(AppNotificationType type) {
    switch (type) {
      case AppNotificationType.lowStock:
        return Colors.orange;
      case AppNotificationType.overdueInvoice:
        return Colors.red;
      case AppNotificationType.system:
        return Colors.blueGrey;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final notificationsAsync = ref.watch(notificationsControllerProvider);
    final dateFormat = DateFormat('MMM d, HH:mm');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          IconButton(
            icon: const Icon(Icons.done_all),
            tooltip: 'Mark all as read',
            onPressed: () => ref.read(notificationsControllerProvider.notifier).markAllRead(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(notificationsControllerProvider.notifier).refresh(),
        child: notificationsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => Center(child: Text(l10n.errorGeneric)),
          data: (notifications) {
            if (notifications.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 80),
                    child: Center(child: Text(l10n.noData)),
                  ),
                ],
              );
            }
            return ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              itemCount: notifications.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final notification = notifications[index];
                final color = _colorFor(notification.type);
                return Card(
                  color: notification.isRead ? null : color.withValues(alpha: 0.08),
                  child: ListTile(
                    leading: Icon(_iconFor(notification.type), color: color),
                    title: Text(
                      notification.title,
                      style: TextStyle(fontWeight: notification.isRead ? FontWeight.normal : FontWeight.bold),
                    ),
                    subtitle: Text(
                      notification.message.isEmpty
                          ? dateFormat.format(notification.createdAt.toLocal())
                          : '${notification.message}\n${dateFormat.format(notification.createdAt.toLocal())}',
                    ),
                    isThreeLine: notification.message.isNotEmpty,
                    trailing: notification.isRead
                        ? null
                        : const Icon(Icons.circle, size: 10, color: Colors.blue),
                    onTap: notification.isRead
                        ? null
                        : () => ref.read(notificationsControllerProvider.notifier).markRead(notification.id),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
