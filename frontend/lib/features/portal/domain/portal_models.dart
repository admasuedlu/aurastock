/// A logged-in external portal user (customer or supplier). Distinct from
/// the staff AppUser: authenticates with a signed `Portal` token, not a JWT.
class PortalSession {
  const PortalSession({
    required this.token,
    required this.accountType,
    required this.displayName,
    required this.email,
  });

  factory PortalSession.fromJson(Map<String, dynamic> json) {
    return PortalSession(
      token: json['token'] as String,
      accountType: json['account_type'] as String,
      displayName: json['display_name'] as String? ?? '',
      email: json['email'] as String? ?? '',
    );
  }

  final String token;
  final String accountType; // 'customer' | 'supplier'
  final String displayName;
  final String email;

  bool get isCustomer => accountType == 'customer';
  bool get isSupplier => accountType == 'supplier';

  Map<String, dynamic> toJson() => {
        'token': token,
        'account_type': accountType,
        'display_name': displayName,
        'email': email,
      };
}

class PortalLineItem {
  const PortalLineItem({
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    required this.lineTotal,
  });

  factory PortalLineItem.fromJson(Map<String, dynamic> json) {
    return PortalLineItem(
      productName: json['product_name'] as String? ?? '',
      quantity: double.tryParse(json['quantity'].toString()) ?? 0,
      unitPrice: double.tryParse(json['unit_price'].toString()) ?? 0,
      lineTotal: double.tryParse(json['line_total'].toString()) ?? 0,
    );
  }

  final String productName;
  final double quantity;
  final double unitPrice;
  final double lineTotal;
}

/// One customer-facing document (quotation / sales order / invoice). They
/// share enough shape that the portal renders them through a single model.
class PortalDocument {
  const PortalDocument({
    required this.id,
    required this.number,
    required this.status,
    required this.total,
    required this.balanceDue,
    required this.items,
  });

  factory PortalDocument.fromJson(Map<String, dynamic> json) {
    final rawItems = (json['items'] as List?) ?? const [];
    return PortalDocument(
      id: json['id'] as String,
      number: json['number'] as String,
      status: json['status'] as String? ?? '',
      total: double.tryParse(json['total'].toString()) ?? 0,
      balanceDue: json['balance_due'] == null
          ? null
          : double.tryParse(json['balance_due'].toString()),
      items: rawItems.map((e) => PortalLineItem.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  final String id;
  final String number;
  final String status;
  final double total;
  final double? balanceDue;
  final List<PortalLineItem> items;
}
