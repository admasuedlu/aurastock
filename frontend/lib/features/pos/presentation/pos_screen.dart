import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../products/providers/product_providers.dart';
import '../providers/pos_providers.dart';
import 'checkout_sheet.dart';
import 'close_session_sheet.dart';
import 'open_session_sheet.dart';
import 'pos_history_sheet.dart';

class PosScreen extends ConsumerWidget {
  const PosScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final sessionAsync = ref.watch(currentSessionProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.pos)),
      body: sessionAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text(l10n.errorGeneric)),
        data: (session) {
          if (session == null) return const OpenSessionView();
          return _SellingView(sessionId: session.id, openingCash: session.openingCash);
        },
      ),
    );
  }
}

class _SellingView extends ConsumerStatefulWidget {
  const _SellingView({required this.sessionId, required this.openingCash});
  final String sessionId;
  final double openingCash;

  @override
  ConsumerState<_SellingView> createState() => _SellingViewState();
}

class _SellingViewState extends ConsumerState<_SellingView> {
  @override
  Widget build(BuildContext context) {
    final productsAsync = ref.watch(productListProvider);
    final cart = ref.watch(cartControllerProvider);
    final cartNotifier = ref.read(cartControllerProvider.notifier);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: const InputDecoration(hintText: 'Search products', prefixIcon: Icon(Icons.search)),
                  onChanged: (value) => ref.read(productSearchProvider.notifier).state = value,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.receipt_long_outlined),
                tooltip: "Today's sales",
                onPressed: () async {
                  final session = await ref.read(currentSessionProvider.future);
                  if (session != null && context.mounted) {
                    showPosHistorySheet(context, ref, session.id);
                  }
                },
              ),
              IconButton(
                icon: const Icon(Icons.lock_clock_outlined),
                tooltip: 'Close session',
                onPressed: () async {
                  final session = await ref.read(currentSessionProvider.future);
                  if (session != null && context.mounted) {
                    showCloseSessionSheet(context, ref, session);
                  }
                },
              ),
            ],
          ),
        ),
        Expanded(
          child: productsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (err, _) => const Center(child: Text('Could not load products.')),
            data: (products) {
              if (products.isEmpty) return const Center(child: Text('No products yet.'));
              return LayoutBuilder(
                builder: (context, constraints) {
                  final columns = constraints.maxWidth >= 900 ? 4 : (constraints.maxWidth >= 600 ? 3 : 2);
                  return GridView.builder(
                    padding: const EdgeInsets.all(16),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: columns,
                      mainAxisSpacing: 12,
                      crossAxisSpacing: 12,
                      childAspectRatio: 1.1,
                    ),
                    itemCount: products.length,
                    itemBuilder: (context, index) {
                      final product = products[index];
                      return Card(
                        child: InkWell(
                          borderRadius: BorderRadius.circular(16),
                          onTap: () => cartNotifier.addProduct(
                            productId: product.id,
                            productName: product.name,
                            sku: product.sku,
                            unitPrice: product.sellingPrice,
                            taxPercent: 15,
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  product.name,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: Theme.of(context).textTheme.titleSmall,
                                ),
                                Text(product.sku, style: Theme.of(context).textTheme.bodySmall),
                                Text(
                                  currency.format(product.sellingPrice),
                                  style: const TextStyle(fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  );
                },
              );
            },
          ),
        ),
        if (cart.isNotEmpty) _CartBar(sessionId: widget.sessionId),
      ],
    );
  }
}

class _CartBar extends ConsumerWidget {
  const _CartBar({required this.sessionId});
  final String sessionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cart = ref.watch(cartControllerProvider);
    final cartNotifier = ref.read(cartControllerProvider.notifier);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);
    final scheme = Theme.of(context).colorScheme;

    return SafeArea(
      top: false,
      child: Material(
        color: scheme.surfaceContainerHigh,
        child: InkWell(
          onTap: () => _showCartSheet(context, ref),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Row(
              children: [
                Badge(
                  label: Text('${cart.fold<int>(0, (sum, i) => sum + i.quantity)}'),
                  child: const Icon(Icons.shopping_cart),
                ),
                const SizedBox(width: 16),
                Expanded(child: Text('${cart.length} item(s)')),
                Text(currency.format(cartNotifier.total), style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: () => showCheckoutSheet(context, sessionId),
                  child: const Text('Checkout'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showCartSheet(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => _CartDetailSheet(sessionId: sessionId),
    );
  }
}

class _CartDetailSheet extends ConsumerWidget {
  const _CartDetailSheet({required this.sessionId});
  final String sessionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cart = ref.watch(cartControllerProvider);
    final cartNotifier = ref.read(cartControllerProvider.notifier);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Cart', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          ...cart.map((item) => ListTile(
                title: Text(item.productName),
                subtitle: Text(currency.format(item.unitPrice)),
                leading: IconButton(
                  icon: const Icon(Icons.remove_circle_outline),
                  onPressed: () => cartNotifier.updateQuantity(item.productId, item.quantity - 1),
                ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('${item.quantity}'),
                    IconButton(
                      icon: const Icon(Icons.add_circle_outline),
                      onPressed: () => cartNotifier.updateQuantity(item.productId, item.quantity + 1),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline),
                      onPressed: () => cartNotifier.removeProduct(item.productId),
                    ),
                  ],
                ),
              )),
          const Divider(),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Total', style: TextStyle(fontWeight: FontWeight.bold)),
              Text(currency.format(cartNotifier.total), style: const TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: cart.isEmpty
                ? null
                : () {
                    Navigator.of(context).pop();
                    showCheckoutSheet(context, sessionId);
                  },
            child: const Text('Checkout'),
          ),
        ],
      ),
    );
  }
}
