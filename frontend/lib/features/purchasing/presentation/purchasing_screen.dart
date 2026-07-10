import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../portal/presentation/portal_access_dialog.dart';
import '../../suppliers/presentation/supplier_form_sheet.dart';
import '../../suppliers/providers/supplier_providers.dart';
import '../providers/purchasing_providers.dart';
import 'create_purchase_order_sheet.dart';
import 'purchase_order_actions_sheet.dart';

class PurchasingScreen extends ConsumerStatefulWidget {
  const PurchasingScreen({super.key});

  @override
  ConsumerState<PurchasingScreen> createState() => _PurchasingScreenState();
}

class _PurchasingScreenState extends ConsumerState<PurchasingScreen> {
  int _tabIndex = 0;

  Color _statusColor(String status, BuildContext context) {
    switch (status) {
      case 'received':
        return Colors.green;
      case 'partially_received':
        return Colors.orange;
      case 'cancelled':
        return Colors.red;
      default:
        return Theme.of(context).colorScheme.outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
    final ordersAsync = ref.watch(purchaseOrderListProvider);
    final suppliersAsync = ref.watch(supplierListProvider);

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.purchases),
          bottom: TabBar(
            onTap: (i) => setState(() => _tabIndex = i),
            tabs: const [Tab(text: 'Purchase Orders'), Tab(text: 'Suppliers')],
          ),
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: _tabIndex == 0
              ? () => showCreatePurchaseOrderSheet(context)
              : () => showSupplierFormSheet(context),
          icon: const Icon(Icons.add),
          label: Text(_tabIndex == 0 ? 'New Purchase Order' : 'Add Supplier'),
        ),
        body: TabBarView(
          children: [
            ordersAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text(l10n.errorGeneric)),
              data: (orders) {
                if (orders.isEmpty) return Center(child: Text(l10n.noData));
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: orders.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final order = orders[index];
                    return Card(
                      child: ListTile(
                        title: Text(order.number),
                        subtitle: Text(order.supplierName),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(currency.format(order.total)),
                            Text(order.status, style: TextStyle(color: _statusColor(order.status, context))),
                          ],
                        ),
                        onTap: () => showPurchaseOrderActionsSheet(context, ref, order),
                      ),
                    );
                  },
                );
              },
            ),
            suppliersAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text(l10n.errorGeneric)),
              data: (suppliers) {
                if (suppliers.isEmpty) return Center(child: Text(l10n.noData));
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: suppliers.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final supplier = suppliers[index];
                    return Card(
                      child: ListTile(
                        leading: CircleAvatar(child: Text(supplier.name.isNotEmpty ? supplier.name[0] : '?')),
                        title: Text(supplier.name),
                        subtitle: Text(supplier.phone.isNotEmpty ? supplier.phone : supplier.email),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('Net ${supplier.paymentTermsDays}'),
                            IconButton(
                              icon: const Icon(Icons.vpn_key_outlined),
                              tooltip: 'Portal access',
                              onPressed: () => showPortalAccessDialog(
                                context,
                                resource: 'suppliers',
                                id: supplier.id,
                                name: supplier.name,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
