import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../domain/pos_models.dart';
import '../providers/pos_providers.dart';

Future<void> showCloseSessionSheet(BuildContext context, WidgetRef ref, PosSession session) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => _CloseSessionSheet(session: session),
  );
}

class _CloseSessionSheet extends ConsumerStatefulWidget {
  const _CloseSessionSheet({required this.session});
  final PosSession session;

  @override
  ConsumerState<_CloseSessionSheet> createState() => _CloseSessionSheetState();
}

class _CloseSessionSheetState extends ConsumerState<_CloseSessionSheet> {
  final _cashController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _cashController.dispose();
    super.dispose();
  }

  Future<void> _close() async {
    final closingCash = double.tryParse(_cashController.text);
    if (closingCash == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter the counted cash amount.')));
      return;
    }
    setState(() => _submitting = true);
    try {
      final closed = await ref.read(posRepositoryProvider).closeSession(widget.session.id, closingCash: closingCash);
      ref.invalidate(currentSessionProvider);
      if (mounted) {
        Navigator.of(context).pop();
        final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Session closed'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Expected cash: ${currency.format(closed.expectedCash ?? 0)}'),
                Text('Counted cash: ${currency.format(closed.closingCash ?? 0)}'),
                Text(
                  'Variance: ${currency.format(closed.cashVariance ?? 0)}',
                  style: TextStyle(
                    color: (closed.cashVariance ?? 0) == 0 ? Colors.green : Colors.orange,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Done'))],
          ),
        );
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20, right: 20, top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Close till session', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text('Opening float: ETB ${widget.session.openingCash.toStringAsFixed(2)}'),
          const SizedBox(height: 16),
          TextFormField(
            controller: _cashController,
            decoration: const InputDecoration(labelText: 'Counted cash in drawer (ETB)'),
            keyboardType: TextInputType.number,
            autofocus: true,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _submitting ? null : _close,
            child: _submitting
                ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Close Session'),
          ),
        ],
      ),
    );
  }
}
