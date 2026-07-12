import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../products/providers/product_providers.dart';
import '../domain/insight_models.dart';
import '../providers/insights_providers.dart';

class InsightsScreen extends StatelessWidget {
  const InsightsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('AI Insights'),
          bottom: const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'Reorder Suggestions'),
              Tab(text: 'Demand Forecast'),
              Tab(text: 'Anomalies'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [_ReorderTab(), _ForecastTab(), _AnomaliesTab()],
        ),
      ),
    );
  }
}

class _ReorderTab extends ConsumerWidget {
  const _ReorderTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final suggestionsAsync = ref.watch(reorderSuggestionsProvider);

    return suggestionsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (rows) {
        if (rows.isEmpty) {
          return const Center(child: Text('Nothing needs reordering right now.'));
        }
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: rows.length,
          separatorBuilder: (_, _) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final row = rows[index];
            return Card(
              child: ListTile(
                leading: const Icon(Icons.trending_up, color: Colors.orange),
                title: Text(row.productName),
                subtitle: Text(
                  '${row.warehouseName} · available ${row.availableQuantity.toStringAsFixed(0)} '
                  '(reorder at ${row.reorderLevel.toStringAsFixed(0)}) · '
                  '~${row.avgDailySales.toStringAsFixed(1)}/day',
                ),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(row.suggestedQuantity.toStringAsFixed(0), style: const TextStyle(fontWeight: FontWeight.bold)),
                    const Text('suggested', style: TextStyle(fontSize: 11)),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}

class _ForecastTab extends ConsumerWidget {
  const _ForecastTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final productsAsync = ref.watch(productListProvider);
    final selectedProductId = ref.watch(selectedForecastProductProvider);
    final forecastAsync = ref.watch(demandForecastProvider);

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          productsAsync.when(
            loading: () => const LinearProgressIndicator(),
            error: (_, _) => const SizedBox.shrink(),
            data: (products) => DropdownButtonFormField<String>(
              initialValue: selectedProductId,
              decoration: const InputDecoration(labelText: 'Product'),
              items: products.map((p) => DropdownMenuItem(value: p.id, child: Text(p.name))).toList(),
              onChanged: (v) => ref.read(selectedForecastProductProvider.notifier).state = v,
            ),
          ),
          const SizedBox(height: 20),
          Expanded(
            child: selectedProductId == null
                ? const Center(child: Text('Pick a product to see its demand forecast.'))
                : forecastAsync.when(
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (err, _) => Center(child: Text(l10n.errorGeneric)),
                    data: (forecast) => forecast == null
                        ? const SizedBox.shrink()
                        : _ForecastChart(forecast: forecast),
                  ),
          ),
        ],
      ),
    );
  }
}

class _ForecastChart extends StatelessWidget {
  const _ForecastChart({required this.forecast});
  final DemandForecast forecast;

  Color _trendColor(BuildContext context) {
    switch (forecast.trend) {
      case 'increasing':
        return Colors.green;
      case 'decreasing':
        return Colors.red;
      default:
        return Theme.of(context).colorScheme.outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final history = forecast.history;
    final forecastPoints = forecast.forecast;
    final allPoints = [...history, ...forecastPoints];
    final maxY = allPoints.map((p) => p.quantity).fold<double>(0, (a, b) => a > b ? a : b);

    final historySpots = [
      for (int i = 0; i < history.length; i++) FlSpot(i.toDouble(), history[i].quantity),
    ];
    final forecastSpots = [
      FlSpot((history.length - 1).toDouble(), history.isNotEmpty ? history.last.quantity : 0),
      for (int i = 0; i < forecastPoints.length; i++)
        FlSpot((history.length + i).toDouble(), forecastPoints[i].quantity),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(forecast.productName, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(width: 12),
            Chip(
              label: Text(forecast.trend),
              backgroundColor: _trendColor(context).withValues(alpha: 0.15),
              labelStyle: TextStyle(color: _trendColor(context)),
            ),
          ],
        ),
        Text('Avg daily demand: ${forecast.avgDailyDemand.toStringAsFixed(1)} units'),
        const SizedBox(height: 16),
        Expanded(
          child: LineChart(
            LineChartData(
              minY: 0,
              maxY: maxY == 0 ? 1 : maxY * 1.2,
              gridData: const FlGridData(show: false),
              titlesData: const FlTitlesData(show: false),
              borderData: FlBorderData(show: false),
              lineBarsData: [
                LineChartBarData(
                  spots: historySpots,
                  isCurved: true,
                  color: scheme.primary,
                  barWidth: 2,
                  dotData: const FlDotData(show: false),
                ),
                LineChartBarData(
                  spots: forecastSpots,
                  isCurved: true,
                  color: scheme.tertiary,
                  barWidth: 2,
                  dashArray: [6, 4],
                  dotData: const FlDotData(show: false),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            _legendDot(scheme.primary, 'History'),
            const SizedBox(width: 16),
            _legendDot(scheme.tertiary, 'Forecast'),
          ],
        ),
      ],
    );
  }

  Widget _legendDot(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text(label),
      ],
    );
  }
}

class _AnomaliesTab extends ConsumerWidget {
  const _AnomaliesTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final anomaliesAsync = ref.watch(anomaliesProvider);
    final dateFormat = DateFormat('MMM d, HH:mm');

    return anomaliesAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (rows) {
        if (rows.isEmpty) {
          return const Center(child: Text('No unusual stock movements detected recently.'));
        }
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: rows.length,
          separatorBuilder: (_, _) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final row = rows[index];
            return Card(
              child: ListTile(
                leading: const Icon(Icons.warning_amber_rounded, color: Colors.red),
                title: Text(row.productName),
                subtitle: Text(
                  '${row.warehouseName} · ${row.reference}\n'
                  '${dateFormat.format(row.occurredAt.toLocal())} · typical ~${row.typicalQuantity.toStringAsFixed(1)}',
                ),
                isThreeLine: true,
                trailing: Text(
                  row.quantity.toStringAsFixed(0),
                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.red),
                ),
              ),
            );
          },
        );
      },
    );
  }
}
