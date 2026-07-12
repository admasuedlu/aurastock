import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../suppliers/providers/supplier_providers.dart';
import '../domain/purchasing_models.dart';
import '../providers/purchasing_providers.dart';

Future<void> showPurchaseRequestActionsSheet(BuildContext context, WidgetRef ref, PurchaseRequest request) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => _PurchaseRequestActionsSheet(request: request),
  );
}

class _PurchaseRequestActionsSheet extends ConsumerStatefulWidget {
  const _PurchaseRequestActionsSheet({required this.request});
  final PurchaseRequest request;

  @override
  ConsumerState<_PurchaseRequestActionsSheet> createState() => _PurchaseRequestActionsSheetState();
}

class _PurchaseRequestActionsSheetState extends ConsumerState<_PurchaseRequestActionsSheet> {
  bool _busy = false;
  String? _supplierId; // only needed when converting a request that has no supplier
  final _reasonController = TextEditingController();

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action, String doneMessage, {bool alsoRefreshOrders = false}) async {
    setState(() => _busy = true);
    try {
      await action();
      ref.invalidate(purchaseRequestListProvider);
      if (alsoRefreshOrders) ref.invalidate(purchaseOrderListProvider);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(doneMessage)));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _convert() {
    final hasSupplier = widget.request.supplierName.isNotEmpty;
    if (!hasSupplier && _supplierId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pick a supplier to order from.')),
      );
      return;
    }
    final repo = ref.read(purchasingRepositoryProvider);
    _run(
      () => repo.convertRequestToPo(widget.request.id, supplierId: hasSupplier ? null : _supplierId),
      'Purchase order created from this request.',
      alsoRefreshOrders: true,
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
    final request = widget.request;
    final repo = ref.read(purchasingRepositoryProvider);

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: 20, right: 20, top: 20,
          bottom: MediaQuery.of(context).viewInsets.bottom + 20,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(request.number, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 4),
              Text('Requested by ${request.requestedByName.isEmpty ? "—" : request.requestedByName}'
                  '${request.supplierName.isEmpty ? "" : " · ${request.supplierName}"}'),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Status: ${request.status}'),
                  Text(currency.format(request.total), style: const TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
              if (request.status == 'rejected' && request.rejectionReason.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text('Rejected: ${request.rejectionReason}',
                    style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
              if (request.approvedByName.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  '${request.status == 'rejected' ? 'Rejected' : 'Approved'} by ${request.approvedByName}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 20),
              if (_busy)
                const Center(child: CircularProgressIndicator())
              else if (request.canSubmit)
                FilledButton.icon(
                  onPressed: () => _run(() => repo.submitPurchaseRequest(request.id), 'Submitted for approval.'),
                  icon: const Icon(Icons.send_outlined),
                  label: const Text('Submit for Approval'),
                )
              else if (request.canApproveOrReject) ...[
                TextField(
                  controller: _reasonController,
                  decoration: const InputDecoration(
                    labelText: 'Rejection reason (optional)',
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: () => _run(() => repo.approvePurchaseRequest(request.id), 'Request approved.'),
                        icon: const Icon(Icons.check),
                        label: const Text('Approve'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _run(
                          () => repo.rejectPurchaseRequest(request.id, reason: _reasonController.text.trim()),
                          'Request rejected.',
                        ),
                        icon: const Icon(Icons.close),
                        label: const Text('Reject'),
                      ),
                    ),
                  ],
                ),
              ] else if (request.canConvert) ...[
                if (request.supplierName.isEmpty)
                  ref.watch(supplierListProvider).when(
                        loading: () => const LinearProgressIndicator(),
                        error: (_, _) => Text(l10n.errorGeneric),
                        data: (suppliers) => DropdownButtonFormField<String>(
                          initialValue: _supplierId,
                          decoration: const InputDecoration(labelText: 'Order from supplier'),
                          items: suppliers
                              .map((s) => DropdownMenuItem(value: s.id, child: Text(s.name)))
                              .toList(),
                          onChanged: (v) => setState(() => _supplierId = v),
                        ),
                      ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: _convert,
                  icon: const Icon(Icons.shopping_cart_checkout),
                  label: const Text('Convert to Purchase Order'),
                ),
              ] else
                Text('No further actions for a ${request.status} request.'),
            ],
          ),
        ),
      ),
    );
  }
}
