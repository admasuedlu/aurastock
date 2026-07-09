class Customer {
  Customer({
    required this.id,
    required this.name,
    required this.phone,
    required this.email,
    required this.creditLimit,
    required this.isActive,
  });

  factory Customer.fromJson(Map<String, dynamic> json) {
    return Customer(
      id: json['id'] as String,
      name: json['name'] as String,
      phone: json['phone'] as String? ?? '',
      email: json['email'] as String? ?? '',
      creditLimit: double.tryParse(json['credit_limit'].toString()) ?? 0,
      isActive: json['is_active'] as bool? ?? true,
    );
  }

  final String id;
  final String name;
  final String phone;
  final String email;
  final double creditLimit;
  final bool isActive;
}
