import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../domain/portal_models.dart';
import '../providers/portal_providers.dart';

final _currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

Color _statusColor(String status, BuildContext context) {
  switch (status) {
    case 'accepted':
    case 'approved':
    case 'paid':
    case 'received':
      return Colors.green;
    case 'sent':
    case 'partially_paid':
    case 'partially_received':
      return Colors.orange;
    case 'rejected':
    case 'cancelled':
    case 'expired':
      return Colors.red;
    default:
      return Theme.of(context).colorScheme.outline;
  }
}

class PortalHomeScreen extends ConsumerWidget {
  const PortalHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(portalSessionControllerProvider).valueOrNull;
    if (session == null) {
      // The router redirects to login when the session drops; this is just a
      // frame-gap guard.
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final logoutButton = IconButton(
      icon: const Icon(Icons.logout),
      tooltip: 'Log out',
      onPressed: () => ref.read(portalSessionControllerProvider.notifier).logout(),
    );

    if (session.isSupplier) {
      return Scaffold(
        appBar: AppBar(
          title: Text(session.displayName.isEmpty ? 'Supplier Portal' : session.displayName),
          actions: [logoutButton],
        ),
        body: const _PurchaseOrdersTab(),
      );
    }

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text(session.displayName.isEmpty ? 'Customer Portal' : session.displayName),
          actions: [logoutButton],
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Quotations'),
              Tab(text: 'Orders'),
              Tab(text: 'Invoices'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [_QuotationsTab(), _OrdersTab(), _InvoicesTab()],
        ),
      ),
    );
  }
}

/// Shared list scaffolding: pull-to-refresh, loading/error/empty states.
class _DocumentList extends StatelessWidget {
  const _DocumentList({
    required this.async,
    required this.onRefresh,
    required this.itemBuilder,
  });

  final AsyncValue<List<PortalDocument>> async;
  final Future<void> Function() onRefresh;
  final Widget Function(PortalDocument) itemBuilder;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return async.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (docs) {
        if (docs.isEmpty) {
          return RefreshIndicator(
            onRefresh: onRefresh,
            child: ListView(children: [
              const SizedBox(height: 120),
              Center(child: Text(l10n.noData)),
            ]),
          );
        }
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: docs.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) => itemBuilder(docs[index]),
          ),
        );
      },
    );
  }
}

class _DocumentCard extends StatelessWidget {
  const _DocumentCard({required this.doc, this.footer});

  final PortalDocument doc;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(doc.number, style: Theme.of(context).textTheme.titleMedium),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: _statusColor(doc.status, context).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    doc.status.replaceAll('_', ' '),
                    style: TextStyle(color: _statusColor(doc.status, context), fontSize: 12),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            for (final item in doc.items)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    Expanded(child: Text('${item.productName} × ${item.quantity.toStringAsFixed(0)}')),
                    Text(_currency.format(item.lineTotal)),
                  ],
                ),
              ),
            const Divider(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)),
                Text(_currency.format(doc.total), style: const TextStyle(fontWeight: FontWeight.bold)),
              ],
            ),
            if (doc.balanceDue != null)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Balance due'),
                  Text(_currency.format(doc.balanceDue!)),
                ],
              ),
            if (footer != null) ...[const SizedBox(height: 8), footer!],
          ],
        ),
      ),
    );
  }
}

class _QuotationsTab extends ConsumerWidget {
  const _QuotationsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(portalQuotationsProvider);
    return _DocumentList(
      async: async,
      onRefresh: () => ref.refresh(portalQuotationsProvider.future),
      itemBuilder: (doc) => _QuotationCard(doc: doc),
    );
  }
}

class _QuotationCard extends ConsumerStatefulWidget {
  const _QuotationCard({required this.doc});
  final PortalDocument doc;

  @override
  ConsumerState<_QuotationCard> createState() => _QuotationCardState();
}

class _QuotationCardState extends ConsumerState<_QuotationCard> {
  bool _busy = false;

  Future<void> _run(Future<void> Function() action, String done) async {
    setState(() => _busy = true);
    try {
      await action();
      ref.invalidate(portalQuotationsProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Action failed. Please try again.')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final doc = widget.doc;
    final repo = ref.read(portalRepositoryProvider);
    Widget? footer;
    if (doc.status == 'sent') {
      footer = _busy
          ? const Center(child: Padding(padding: EdgeInsets.all(4), child: CircularProgressIndicator()))
          : Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => _run(() => repo.acceptQuotation(doc.id), 'Quotation accepted.'),
                    icon: const Icon(Icons.check),
                    label: const Text('Accept'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _run(() => repo.rejectQuotation(doc.id), 'Quotation rejected.'),
                    icon: const Icon(Icons.close),
                    label: const Text('Reject'),
                  ),
                ),
              ],
            );
    }
    return _DocumentCard(doc: doc, footer: footer);
  }
}

class _OrdersTab extends ConsumerWidget {
  const _OrdersTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(portalSalesOrdersProvider);
    return _DocumentList(
      async: async,
      onRefresh: () => ref.refresh(portalSalesOrdersProvider.future),
      itemBuilder: (doc) => _DocumentCard(doc: doc),
    );
  }
}

class _InvoicesTab extends ConsumerWidget {
  const _InvoicesTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(portalInvoicesProvider);
    return _DocumentList(
      async: async,
      onRefresh: () => ref.refresh(portalInvoicesProvider.future),
      itemBuilder: (doc) => _DocumentCard(doc: doc),
    );
  }
}

class _PurchaseOrdersTab extends ConsumerWidget {
  const _PurchaseOrdersTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(portalPurchaseOrdersProvider);
    return _DocumentList(
      async: async,
      onRefresh: () => ref.refresh(portalPurchaseOrdersProvider.future),
      itemBuilder: (doc) => _PurchaseOrderCard(doc: doc),
    );
  }
}

class _PurchaseOrderCard extends ConsumerStatefulWidget {
  const _PurchaseOrderCard({required this.doc});
  final PortalDocument doc;

  @override
  ConsumerState<_PurchaseOrderCard> createState() => _PurchaseOrderCardState();
}

class _PurchaseOrderCardState extends ConsumerState<_PurchaseOrderCard> {
  bool _busy = false;

  Future<void> _acknowledge() async {
    setState(() => _busy = true);
    try {
      await ref.read(portalRepositoryProvider).acknowledgePurchaseOrder(widget.doc.id);
      ref.invalidate(portalPurchaseOrdersProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Purchase order acknowledged.')));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Action failed. Please try again.')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final doc = widget.doc;
    Widget? footer;
    if (doc.status == 'sent') {
      footer = _busy
          ? const Center(child: Padding(padding: EdgeInsets.all(4), child: CircularProgressIndicator()))
          : FilledButton.icon(
              onPressed: _acknowledge,
              icon: const Icon(Icons.thumb_up_outlined),
              label: const Text('Acknowledge order'),
            );
    }
    return _DocumentCard(doc: doc, footer: footer);
  }
}
