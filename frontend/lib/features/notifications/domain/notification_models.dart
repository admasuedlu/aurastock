enum AppNotificationType { lowStock, overdueInvoice, system }

AppNotificationType _typeFromJson(String value) {
  switch (value) {
    case 'low_stock':
      return AppNotificationType.lowStock;
    case 'overdue_invoice':
      return AppNotificationType.overdueInvoice;
    default:
      return AppNotificationType.system;
  }
}

class AppNotification {
  AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.message,
    required this.reference,
    required this.isRead,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) => AppNotification(
        id: json['id'] as String,
        type: _typeFromJson(json['notification_type'] as String),
        title: json['title'] as String,
        message: json['message'] as String? ?? '',
        reference: json['reference'] as String? ?? '',
        isRead: json['is_read'] as bool,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  final String id;
  final AppNotificationType type;
  final String title;
  final String message;
  final String reference;
  final bool isRead;
  final DateTime createdAt;

  AppNotification copyWith({bool? isRead}) => AppNotification(
        id: id,
        type: type,
        title: title,
        message: message,
        reference: reference,
        isRead: isRead ?? this.isRead,
        createdAt: createdAt,
      );
}
