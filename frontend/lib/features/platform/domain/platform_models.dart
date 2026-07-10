class PlatformOverview {
  PlatformOverview({
    required this.totalCompanies,
    required this.statusCounts,
    required this.totalTenantUsers,
    required this.signupsLast30Days,
  });

  factory PlatformOverview.fromJson(Map<String, dynamic> json) => PlatformOverview(
        totalCompanies: json['total_companies'] as int,
        statusCounts: (json['status_counts'] as Map<String, dynamic>)
            .map((k, v) => MapEntry(k, v as int)),
        totalTenantUsers: json['total_tenant_users'] as int,
        signupsLast30Days: json['signups_last_30_days'] as int,
      );

  final int totalCompanies;
  final Map<String, int> statusCounts;
  final int totalTenantUsers;
  final int signupsLast30Days;
}

class SaasPlan {
  SaasPlan({
    required this.id,
    required this.name,
    required this.code,
    required this.priceMonthlyEtb,
    required this.maxUsers,
    required this.maxBranches,
    required this.maxWarehouses,
    required this.isActive,
    required this.companyCount,
  });

  factory SaasPlan.fromJson(Map<String, dynamic> json) => SaasPlan(
        id: json['id'] as String,
        name: json['name'] as String,
        code: json['code'] as String,
        priceMonthlyEtb: double.tryParse(json['price_monthly_etb'].toString()) ?? 0,
        maxUsers: json['max_users'] as int,
        maxBranches: json['max_branches'] as int,
        maxWarehouses: json['max_warehouses'] as int,
        isActive: json['is_active'] as bool,
        companyCount: json['company_count'] as int? ?? 0,
      );

  final String id;
  final String name;
  final String code;
  final double priceMonthlyEtb;
  final int maxUsers;
  final int maxBranches;
  final int maxWarehouses;
  final bool isActive;
  final int companyCount;
}

class TenantCompany {
  TenantCompany({
    required this.id,
    required this.name,
    required this.slug,
    required this.email,
    required this.phone,
    required this.city,
    required this.planId,
    required this.planName,
    required this.planCode,
    required this.subscriptionStatus,
    required this.isActive,
    required this.userCount,
    required this.branchCount,
    required this.warehouseCount,
    required this.createdAt,
  });

  factory TenantCompany.fromJson(Map<String, dynamic> json) => TenantCompany(
        id: json['id'] as String,
        name: json['name'] as String,
        slug: json['slug'] as String? ?? '',
        email: json['email'] as String? ?? '',
        phone: json['phone'] as String? ?? '',
        city: json['city'] as String? ?? '',
        planId: json['subscription_plan'] as String?,
        planName: json['plan_name'] as String? ?? '',
        planCode: json['plan_code'] as String? ?? '',
        subscriptionStatus: json['subscription_status'] as String,
        isActive: json['is_active'] as bool,
        userCount: json['user_count'] as int? ?? 0,
        branchCount: json['branch_count'] as int? ?? 0,
        warehouseCount: json['warehouse_count'] as int? ?? 0,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  final String id;
  final String name;
  final String slug;
  final String email;
  final String phone;
  final String city;
  final String? planId;
  final String planName;
  final String planCode;
  final String subscriptionStatus;
  final bool isActive;
  final int userCount;
  final int branchCount;
  final int warehouseCount;
  final DateTime createdAt;

  bool get isSuspended => subscriptionStatus == 'suspended';
}
