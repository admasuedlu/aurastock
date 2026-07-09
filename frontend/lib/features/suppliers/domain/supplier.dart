class Supplier {
  Supplier({
    required this.id,
    required this.name,
    required this.phone,
    required this.email,
    required this.paymentTermsDays,
    required this.isActive,
  });

  factory Supplier.fromJson(Map<String, dynamic> json) {
    return Supplier(
      id: json['id'] as String,
      name: json['name'] as String,
      phone: json['phone'] as String? ?? '',
      email: json['email'] as String? ?? '',
      paymentTermsDays: json['payment_terms_days'] as int? ?? 30,
      isActive: json['is_active'] as bool? ?? true,
    );
  }

  final String id;
  final String name;
  final String phone;
  final String email;
  final int paymentTermsDays;
  final bool isActive;
}
