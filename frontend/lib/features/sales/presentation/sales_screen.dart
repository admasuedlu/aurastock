import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../customers/presentation/customer_form_sheet.dart';
import '../../customers/providers/customer_providers.dart';
import '../providers/sales_providers.dart';
import 'create_invoice_sheet.dart';
import 'create_sales_order_sheet.dart';
import 'invoice_actions_sheet.dart';

class SalesScreen extends ConsumerStatefulWidget {
  const SalesScreen({super.key});

  @override
  ConsumerState<SalesScreen> createState() => _SalesScreenState();
}

class _SalesScreenState extends ConsumerState<SalesScreen> {
  int _tabIndex = 0;

  Color _statusColor(String status, BuildContext context) {
    switch (status) {
      case 'paid':
      case 'fulfilled':
      case 'confirmed':
        return Colors.green;
      case 'partially_paid':
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
    final salesOrdersAsync = ref.watch(salesOrderListProvider);
    final invoicesAsync = ref.watch(invoiceListProvider);
    final customersAsync = ref.watch(customerListProvider);

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.sales),
          bottom: TabBar(
            onTap: (i) => setState(() => _tabIndex = i),
            tabs: const [Tab(text: 'Sales Orders'), Tab(text: 'Invoices'), Tab(text: 'Customers')],
          ),
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: switch (_tabIndex) {
            0 => () => showCreateSalesOrderSheet(context),
            1 => () => showCreateInvoiceSheet(context),
            _ => () => showCustomerFormSheet(context),
          },
          icon: const Icon(Icons.add),
          label: Text(switch (_tabIndex) {
            0 => 'New Order',
            1 => 'New Invoice',
            _ => 'Add Customer',
          }),
        ),
        body: TabBarView(
          children: [
            salesOrdersAsync.when(
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
                        subtitle: Text(order.customerName),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(currency.format(order.total)),
                            Text(order.status, style: TextStyle(color: _statusColor(order.status, context))),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
            invoicesAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text(l10n.errorGeneric)),
              data: (invoices) {
                if (invoices.isEmpty) return Center(child: Text(l10n.noData));
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: invoices.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final invoice = invoices[index];
                    return Card(
                      child: ListTile(
                        title: Text(invoice.number),
                        subtitle: Text(invoice.customerName),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(currency.format(invoice.total)),
                            Text(invoice.status, style: TextStyle(color: _statusColor(invoice.status, context))),
                          ],
                        ),
                        onTap: () => showInvoiceActionsSheet(context, ref, invoice),
                      ),
                    );
                  },
                );
              },
            ),
            customersAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text(l10n.errorGeneric)),
              data: (customers) {
                if (customers.isEmpty) return Center(child: Text(l10n.noData));
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: customers.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final customer = customers[index];
                    return Card(
                      child: ListTile(
                        leading: CircleAvatar(child: Text(customer.name.isNotEmpty ? customer.name[0] : '?')),
                        title: Text(customer.name),
                        subtitle: Text(customer.phone.isNotEmpty ? customer.phone : customer.email),
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
