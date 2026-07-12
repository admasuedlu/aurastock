import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../providers/pos_providers.dart';

Future<void> showPosHistorySheet(BuildContext context, WidgetRef ref, String sessionId) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    builder: (context) => _PosHistorySheet(sessionId: sessionId),
  );
}

class _PosHistorySheet extends ConsumerWidget {
  const _PosHistorySheet({required this.sessionId});
  final String sessionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final transactionsAsync = ref.watch(sessionTransactionsProvider(sessionId));
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return DraggableScrollableSheet(
      initialChildSize: 0.7,
      maxChildSize: 0.9,
      expand: false,
      builder: (context, scrollController) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text("Today's Sales", style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              Expanded(
                child: transactionsAsync.when(
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (err, _) => const Center(child: Text('Could not load sales history.')),
                  data: (transactions) {
                    if (transactions.isEmpty) return const Center(child: Text('No sales yet this session.'));
                    return ListView.separated(
                      controller: scrollController,
                      itemCount: transactions.length,
                      separatorBuilder: (_, _) => const Divider(),
                      itemBuilder: (context, index) {
                        final txn = transactions[index];
                        final isRefunded = txn.status == 'refunded';
                        return ListTile(
                          title: Text(txn.number),
                          subtitle: Text('${txn.customerName} · ${txn.paymentMethod}'),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text(
                                currency.format(txn.total),
                                style: TextStyle(
                                  decoration: isRefunded ? TextDecoration.lineThrough : null,
                                ),
                              ),
                              if (!isRefunded)
                                TextButton(
                                  onPressed: () async {
                                    try {
                                      await ref.read(posRepositoryProvider).refundTransaction(txn.id);
                                      ref.invalidate(sessionTransactionsProvider(sessionId));
                                    } catch (e) {
                                      if (context.mounted) {
                                        ScaffoldMessenger.of(context)
                                            .showSnackBar(SnackBar(content: Text(e.toString())));
                                      }
                                    }
                                  },
                                  child: const Text('Refund'),
                                )
                              else
                                const Text('Refunded', style: TextStyle(color: Colors.red, fontSize: 12)),
                            ],
                          ),
                        );
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
