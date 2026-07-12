import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../providers/product_providers.dart';
import 'bundle_sheet.dart';
import 'product_form_sheet.dart';

class ProductListScreen extends ConsumerWidget {
  const ProductListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final productsAsync = ref.watch(productListProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.products),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(60),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: TextField(
              decoration: InputDecoration(
                hintText: l10n.search,
                prefixIcon: const Icon(Icons.search),
              ),
              onChanged: (value) => ref.read(productSearchProvider.notifier).state = value,
            ),
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => showProductFormSheet(context),
        icon: const Icon(Icons.add),
        label: Text(l10n.addProduct),
      ),
      body: productsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text(l10n.errorGeneric)),
        data: (products) {
          if (products.isEmpty) {
            return Center(child: Text(l10n.noData));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: products.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final product = products[index];
              return Card(
                child: ListTile(
                  leading: CircleAvatar(child: Text(product.name.isNotEmpty ? product.name[0] : '?')),
                  title: Text(product.name),
                  subtitle: Text('${product.sku} · ${product.categoryName}'),
                  trailing: product.isBundle
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(currency.format(product.sellingPrice)),
                            IconButton(
                              icon: const Icon(Icons.precision_manufacturing_outlined),
                              tooltip: 'Bundle components / assemble',
                              onPressed: () => showBundleSheet(context, product),
                            ),
                          ],
                        )
                      : Text(currency.format(product.sellingPrice)),
                  onTap: product.isBundle ? () => showBundleSheet(context, product) : null,
                ),
              );
            },
          );
        },
      ),
    );
  }
}
