import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/providers/auth_controller.dart';
import '../../inventory/providers/inventory_providers.dart';
import '../../products/providers/product_providers.dart';
import '../../reports/domain/report_models.dart';
import '../../reports/providers/reports_providers.dart';
import 'widgets/kpi_card.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final user = ref.watch(authControllerProvider).valueOrNull;
    final productsAsync = ref.watch(productListProvider);
    final stockAsync = ref.watch(stockItemListProvider);
    final salesSummaryAsync = ref.watch(salesSummaryProvider);
    final currency = NumberFormat.currency(symbol: 'ETB ', decimalDigits: 2);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.dashboard),
        actions: [
          IconButton(
            icon: const Icon(Icons.bar_chart_outlined),
            tooltip: l10n.reports,
            onPressed: () => context.go('/reports'),
          ),
          IconButton(
            icon: const Icon(Icons.auto_awesome_outlined),
            tooltip: 'AI Insights',
            onPressed: () => context.go('/insights'),
          ),
          if (user != null)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(child: Text(user.fullName.isEmpty ? user.email : user.fullName)),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(productListProvider);
          ref.invalidate(stockItemListProvider);
          ref.invalidate(salesSummaryProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          child: stockAsync.when(
            loading: () => const Padding(
              padding: EdgeInsets.only(top: 80),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (err, _) => Padding(
              padding: const EdgeInsets.only(top: 80),
              child: Center(child: Text(l10n.errorGeneric)),
            ),
            data: (stockItems) {
              final inventoryValue = stockItems.fold<double>(0, (sum, item) => sum + item.stockValue);
              final lowStockCount = stockItems.where((item) => item.isLowStock).length;
              final productCount = productsAsync.valueOrNull?.length ?? 0;
              final todaySales = salesSummaryAsync.valueOrNull?.todayTotal ?? 0;
              final monthRevenue = salesSummaryAsync.valueOrNull?.monthTotal ?? 0;

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final columns = constraints.maxWidth >= 900 ? 4 : (constraints.maxWidth >= 600 ? 2 : 1);
                      return GridView.count(
                        crossAxisCount: columns,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        mainAxisSpacing: 16,
                        crossAxisSpacing: 16,
                        childAspectRatio: 1.5,
                        children: [
                          KpiCard(
                            label: l10n.todaySales,
                            value: currency.format(todaySales),
                            icon: Icons.point_of_sale_outlined,
                          ),
                          KpiCard(
                            label: l10n.monthlyRevenue,
                            value: currency.format(monthRevenue),
                            icon: Icons.trending_up,
                          ),
                          KpiCard(
                            label: l10n.inventoryValue,
                            value: currency.format(inventoryValue),
                            icon: Icons.account_balance_wallet_outlined,
                          ),
                          KpiCard(
                            label: l10n.totalProducts,
                            value: '$productCount',
                            icon: Icons.inventory_2_outlined,
                          ),
                          KpiCard(
                            label: l10n.lowStockItems,
                            value: '$lowStockCount',
                            icon: Icons.warning_amber_rounded,
                            color: lowStockCount > 0 ? Colors.orange : null,
                          ),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 28),
                  Text('Sales — last 30 days', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 200,
                    child: salesSummaryAsync.when(
                      loading: () => const Center(child: CircularProgressIndicator()),
                      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
                      data: (summary) => _SalesTrendChart(summary: summary, currency: currency),
                    ),
                  ),
                  const SizedBox(height: 28),
                  Text(l10n.lowStockItems, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  if (lowStockCount == 0)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 24),
                      child: Text(l10n.noData, style: Theme.of(context).textTheme.bodyMedium),
                    )
                  else
                    Card(
                      child: Column(
                        children: stockItems.where((item) => item.isLowStock).map((item) {
                          return ListTile(
                            leading: const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                            title: Text(item.productName),
                            subtitle: Text('${item.warehouseName} · ${item.productSku}'),
                            trailing: Text('${item.quantityOnHand.toStringAsFixed(0)} / ${item.reorderLevel.toStringAsFixed(0)}'),
                          );
                        }).toList(),
                      ),
                    ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _SalesTrendChart extends StatelessWidget {
  const _SalesTrendChart({required this.summary, required this.currency});
  final SalesSummary summary;
  final NumberFormat currency;

  @override
  Widget build(BuildContext context) {
    final series = summary.series;
    if (series.isEmpty || series.every((p) => p.total == 0)) {
      return Center(
        child: Text('No sales yet in this period', style: Theme.of(context).textTheme.bodyMedium),
      );
    }
    final scheme = Theme.of(context).colorScheme;
    final spots = [
      for (int i = 0; i < series.length; i++) FlSpot(i.toDouble(), series[i].total),
    ];
    final maxY = spots.map((s) => s.y).fold<double>(0, (a, b) => a > b ? a : b);

    return LineChart(
      LineChartData(
        minY: 0,
        maxY: maxY == 0 ? 1 : maxY * 1.2,
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) => touchedSpots.map((spot) {
              final point = series[spot.x.toInt()];
              final date = point.date;
              return LineTooltipItem(
                '${date.month}/${date.day}\n${currency.format(spot.y)}',
                const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              );
            }).toList(),
          ),
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: scheme.primary,
            barWidth: 3,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(show: true, color: scheme.primary.withValues(alpha: 0.12)),
          ),
        ],
      ),
    );
  }
}
