import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../auth/providers/auth_controller.dart';
import '../domain/platform_models.dart';
import '../providers/platform_providers.dart';

class PlatformScreen extends ConsumerWidget {
  const PlatformScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Platform Admin'),
          actions: [
            IconButton(
              icon: const Icon(Icons.logout),
              tooltip: 'Log out',
              onPressed: () => ref.read(authControllerProvider.notifier).logout(),
            ),
          ],
          bottom: const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'Overview'),
              Tab(text: 'Companies'),
              Tab(text: 'Plans'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [_OverviewTab(), _CompaniesTab(), _PlansTab()],
        ),
      ),
    );
  }
}

class _OverviewTab extends ConsumerWidget {
  const _OverviewTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final overviewAsync = ref.watch(platformOverviewProvider);

    return overviewAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text(l10n.errorGeneric)),
      data: (overview) {
        final tiles = <(String, String)>[
          ('Companies', '${overview.totalCompanies}'),
          ('Tenant users', '${overview.totalTenantUsers}'),
          ('Signups (30d)', '${overview.signupsLast30Days}'),
          for (final entry in overview.statusCounts.entries)
            (entry.key.replaceAll('_', ' '), '${entry.value}'),
        ];
        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(platformOverviewProvider),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(20),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final columns = constraints.maxWidth >= 900 ? 4 : (constraints.maxWidth >= 600 ? 3 : 2);
                return GridView.count(
                  crossAxisCount: columns,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  childAspectRatio: 1.8,
                  children: [
                    for (final (label, value) in tiles)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(value, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                              const SizedBox(height: 4),
                              Text(label, style: Theme.of(context).textTheme.bodySmall),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              },
            ),
          ),
        );
      },
    );
  }
}

class _CompaniesTab extends ConsumerWidget {
  const _CompaniesTab();

  Color _statusColor(String status) {
    switch (status) {
      case 'active':
        return Colors.green;
      case 'trialing':
        return Colors.blue;
      case 'suspended':
        return Colors.red;
      case 'past_due':
        return Colors.orange;
      default:
        return Colors.blueGrey;
    }
  }

  Future<void> _changePlan(BuildContext context, WidgetRef ref, TenantCompany company) async {
    final plans = await ref.read(platformRepositoryProvider).fetchPlans();
    if (!context.mounted) return;
    String? selected = company.planId;
    final chosen = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Change plan — ${company.name}'),
        content: StatefulBuilder(
          builder: (context, setState) => DropdownButtonFormField<String>(
            initialValue: plans.any((p) => p.id == selected) ? selected : null,
            decoration: const InputDecoration(labelText: 'Plan'),
            items: [
              for (final plan in plans.where((p) => p.isActive))
                DropdownMenuItem(value: plan.id, child: Text('${plan.name} (${plan.priceMonthlyEtb.toStringAsFixed(0)} ETB/mo)')),
            ],
            onChanged: (v) => setState(() => selected = v),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, selected), child: const Text('Save')),
        ],
      ),
    );
    if (chosen == null || chosen == company.planId) return;
    await ref.read(platformRepositoryProvider).changePlan(company.id, chosen);
    ref.invalidate(tenantCompaniesProvider);
    ref.invalidate(saasPlansProvider);
  }

  Future<void> _toggleSuspension(WidgetRef ref, TenantCompany company) async {
    final repo = ref.read(platformRepositoryProvider);
    if (company.isSuspended) {
      await repo.activateCompany(company.id);
    } else {
      await repo.suspendCompany(company.id);
    }
    ref.invalidate(tenantCompaniesProvider);
    ref.invalidate(platformOverviewProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final companiesAsync = ref.watch(tenantCompaniesProvider);
    final dateFormat = DateFormat('MMM d, yyyy');

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: TextField(
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Search companies…',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            onSubmitted: (v) => ref.read(tenantSearchProvider.notifier).state = v,
          ),
        ),
        Expanded(
          child: companiesAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (err, _) => Center(child: Text(l10n.errorGeneric)),
            data: (companies) {
              if (companies.isEmpty) {
                return Center(child: Text(l10n.noData));
              }
              return RefreshIndicator(
                onRefresh: () async => ref.invalidate(tenantCompaniesProvider),
                child: ListView.separated(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  itemCount: companies.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final company = companies[index];
                    final color = _statusColor(company.subscriptionStatus);
                    return Card(
                      child: ListTile(
                        title: Row(
                          children: [
                            Flexible(child: Text(company.name, style: const TextStyle(fontWeight: FontWeight.bold))),
                            const SizedBox(width: 8),
                            Chip(
                              label: Text(company.subscriptionStatus.replaceAll('_', ' ')),
                              backgroundColor: color.withValues(alpha: 0.12),
                              labelStyle: TextStyle(color: color, fontSize: 12),
                              visualDensity: VisualDensity.compact,
                            ),
                          ],
                        ),
                        subtitle: Text(
                          '${company.planName.isEmpty ? "no plan" : company.planName} · '
                          '${company.userCount} users · ${company.branchCount} branches · '
                          '${company.warehouseCount} warehouses · since ${dateFormat.format(company.createdAt.toLocal())}',
                        ),
                        trailing: PopupMenuButton<String>(
                          onSelected: (action) {
                            if (action == 'toggle') _toggleSuspension(ref, company);
                            if (action == 'plan') _changePlan(context, ref, company);
                          },
                          itemBuilder: (context) => [
                            PopupMenuItem(
                              value: 'toggle',
                              child: Text(company.isSuspended ? 'Reactivate' : 'Suspend'),
                            ),
                            const PopupMenuItem(value: 'plan', child: Text('Change plan')),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _PlansTab extends ConsumerWidget {
  const _PlansTab();

  Future<void> _editPlan(BuildContext context, WidgetRef ref, {SaasPlan? plan}) async {
    final nameController = TextEditingController(text: plan?.name ?? '');
    final codeController = TextEditingController(text: plan?.code ?? '');
    final priceController = TextEditingController(text: plan?.priceMonthlyEtb.toStringAsFixed(2) ?? '0.00');
    final usersController = TextEditingController(text: '${plan?.maxUsers ?? 5}');
    final branchesController = TextEditingController(text: '${plan?.maxBranches ?? 1}');
    final warehousesController = TextEditingController(text: '${plan?.maxWarehouses ?? 1}');
    final formKey = GlobalKey<FormState>();

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(plan == null ? 'New plan' : 'Edit ${plan.name}'),
        content: Form(
          key: formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: nameController,
                  decoration: const InputDecoration(labelText: 'Name'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                TextFormField(
                  controller: codeController,
                  decoration: const InputDecoration(labelText: 'Code (slug)'),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                TextFormField(
                  controller: priceController,
                  decoration: const InputDecoration(labelText: 'Price / month (ETB)'),
                  keyboardType: TextInputType.number,
                  validator: (v) => double.tryParse(v ?? '') == null ? 'Enter a number' : null,
                ),
                TextFormField(
                  controller: usersController,
                  decoration: const InputDecoration(labelText: 'Max users'),
                  keyboardType: TextInputType.number,
                  validator: (v) => int.tryParse(v ?? '') == null ? 'Enter a whole number' : null,
                ),
                TextFormField(
                  controller: branchesController,
                  decoration: const InputDecoration(labelText: 'Max branches'),
                  keyboardType: TextInputType.number,
                  validator: (v) => int.tryParse(v ?? '') == null ? 'Enter a whole number' : null,
                ),
                TextFormField(
                  controller: warehousesController,
                  decoration: const InputDecoration(labelText: 'Max warehouses'),
                  keyboardType: TextInputType.number,
                  validator: (v) => int.tryParse(v ?? '') == null ? 'Enter a whole number' : null,
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              if (formKey.currentState!.validate()) Navigator.pop(context, true);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (saved != true) return;
    await ref.read(platformRepositoryProvider).savePlan(
          id: plan?.id,
          name: nameController.text.trim(),
          code: codeController.text.trim(),
          priceMonthlyEtb: priceController.text.trim(),
          maxUsers: int.parse(usersController.text.trim()),
          maxBranches: int.parse(branchesController.text.trim()),
          maxWarehouses: int.parse(warehousesController.text.trim()),
        );
    ref.invalidate(saasPlansProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final plansAsync = ref.watch(saasPlansProvider);

    return Scaffold(
      floatingActionButton: FloatingActionButton(
        onPressed: () => _editPlan(context, ref),
        tooltip: 'New plan',
        child: const Icon(Icons.add),
      ),
      body: plansAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text(l10n.errorGeneric)),
        data: (plans) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(saasPlansProvider),
          child: ListView.separated(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            itemCount: plans.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final plan = plans[index];
              return Card(
                child: ListTile(
                  title: Text('${plan.name} — ${plan.priceMonthlyEtb.toStringAsFixed(0)} ETB/mo'),
                  subtitle: Text(
                    '${plan.code} · up to ${plan.maxUsers} users / ${plan.maxBranches} branches / '
                    '${plan.maxWarehouses} warehouses · ${plan.companyCount} companies on it',
                  ),
                  trailing: const Icon(Icons.edit_outlined),
                  onTap: () => _editPlan(context, ref, plan: plan),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
