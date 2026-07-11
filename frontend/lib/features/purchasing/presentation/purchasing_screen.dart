import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../portal/presentation/portal_access_dialog.dart';
import '../../suppliers/presentation/supplier_form_sheet.dart';
import '../../suppliers/providers/supplier_providers.dart';
import '../providers/purchasing_providers.dart';
import 'create_purchase_order_sheet.dart';
import 'create_purchase_request_sheet.dart';
import 'purchase_order_actions_sheet.dart';
import 'purchase_request_actions_sheet.dart';

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
      case 'approved':
      case 'converted':
        return Colors.green;
      case 'partially_received':
      case 'submitted':
        return Colors.orange;
      case 'cancelled':
      case 'rejected':
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
    final requestsAsync = ref.watch(purchaseRequestListProvider);
    final suppliersAsync = ref.watch(supplierListProvider);

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.purchases),
          bottom: TabBar(
            isScrollable: true,
            onTap: (i) => setState(() => _tabIndex = i),
            tabs: const [
              Tab(text: 'Purchase Orders'),
              Tab(text: 'Requests'),
              Tab(text: 'Suppliers'),
            ],
          ),
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: switch (_tabIndex) {
            0 => () => showCreatePurchaseOrderSheet(context),
            1 => () => showCreatePurchaseRequestSheet(context),
            _ => () => showSupplierFormSheet(context),
          },
          icon: const Icon(Icons.add),
          label: Text(switch (_tabIndex) {
            0 => 'New Purchase Order',
            1 => 'New Request',
            _ => 'Add Supplier',
          }),
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
            requestsAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text(l10n.errorGeneric)),
              data: (requests) {
                if (requests.isEmpty) return Center(child: Text(l10n.noData));
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: requests.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final request = requests[index];
                    return Card(
                      child: ListTile(
                        title: Text(request.number),
                        subtitle: Text(request.supplierName.isEmpty
                            ? 'Requested by ${request.requestedByName}'
                            : request.supplierName),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(currency.format(request.total)),
                            Text(request.status, style: TextStyle(color: _statusColor(request.status, context))),
                          ],
                        ),
                        onTap: () => showPurchaseRequestActionsSheet(context, ref, request),
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
