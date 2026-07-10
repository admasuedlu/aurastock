import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/generated/app_localizations.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.child});

  final Widget child;

  static const _destinations = [
    '/', '/pos', '/products', '/inventory', '/sales', '/purchases', '/accounting', '/settings',
  ];

  int _indexForLocation(String location) {
    final index = _destinations.indexWhere((d) => location == d || location.startsWith('$d/'));
    return index == -1 ? 0 : index;
  }

  List<NavigationDestinationLabel> _labels(AppLocalizations l10n) => [
        NavigationDestinationLabel(l10n.dashboard, Icons.dashboard_outlined, Icons.dashboard),
        NavigationDestinationLabel(l10n.pos, Icons.point_of_sale_outlined, Icons.point_of_sale),
        NavigationDestinationLabel(l10n.products, Icons.inventory_2_outlined, Icons.inventory_2),
        NavigationDestinationLabel(l10n.inventory, Icons.warehouse_outlined, Icons.warehouse),
        NavigationDestinationLabel(l10n.sales, Icons.receipt_long_outlined, Icons.receipt_long),
        NavigationDestinationLabel(l10n.purchases, Icons.shopping_cart_outlined, Icons.shopping_cart),
        NavigationDestinationLabel(l10n.accounting, Icons.account_balance_outlined, Icons.account_balance),
        NavigationDestinationLabel(l10n.settings, Icons.settings_outlined, Icons.settings),
      ];

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final location = GoRouterState.of(context).uri.path;
    final currentIndex = _indexForLocation(location);
    final labels = _labels(l10n);
    final isWide = MediaQuery.sizeOf(context).width >= 800;

    void onSelect(int index) => context.go(_destinations[index]);

    if (isWide) {
      return Scaffold(
        body: Row(
          children: [
            NavigationRail(
              selectedIndex: currentIndex,
              onDestinationSelected: onSelect,
              labelType: NavigationRailLabelType.all,
              leading: const Padding(
                padding: EdgeInsets.symmetric(vertical: 16),
                child: Icon(Icons.inventory_2_rounded, size: 32),
              ),
              destinations: labels
                  .map((l) => NavigationRailDestination(
                        icon: Icon(l.icon),
                        selectedIcon: Icon(l.selectedIcon),
                        label: Text(l.label),
                      ))
                  .toList(),
            ),
            const VerticalDivider(width: 1),
            Expanded(child: child),
          ],
        ),
      );
    }

    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: onSelect,
        destinations: labels
            .map((l) => NavigationDestination(icon: Icon(l.icon), selectedIcon: Icon(l.selectedIcon), label: l.label))
            .toList(),
      ),
    );
  }
}

class NavigationDestinationLabel {
  NavigationDestinationLabel(this.label, this.icon, this.selectedIcon);
  final String label;
  final IconData icon;
  final IconData selectedIcon;
}
