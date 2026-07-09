class AppUser {
  const AppUser({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.phone,
    required this.companyId,
    required this.roleName,
    required this.isCompanyOwner,
    required this.preferredLanguage,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: json['id'] as int,
      username: json['username'] as String? ?? '',
      email: json['email'] as String? ?? '',
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      companyId: json['company'] as String?,
      roleName: json['role_name'] as String? ?? '',
      isCompanyOwner: json['is_company_owner'] as bool? ?? false,
      preferredLanguage: json['preferred_language'] as String? ?? 'en',
    );
  }

  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final String phone;
  final String? companyId;
  final String roleName;
  final bool isCompanyOwner;
  final String preferredLanguage;

  String get fullName => [firstName, lastName].where((s) => s.isNotEmpty).join(' ');
}
