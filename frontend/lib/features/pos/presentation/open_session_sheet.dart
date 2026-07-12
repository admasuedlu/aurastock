import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../../inventory/providers/inventory_providers.dart';
import '../providers/pos_providers.dart';

class OpenSessionView extends ConsumerStatefulWidget {
  const OpenSessionView({super.key});

  @override
  ConsumerState<OpenSessionView> createState() => _OpenSessionViewState();
}

class _OpenSessionViewState extends ConsumerState<OpenSessionView> {
  String? _warehouseId;
  final _cashController = TextEditingController(text: '0');
  bool _submitting = false;

  @override
  void dispose() {
    _cashController.dispose();
    super.dispose();
  }

  Future<void> _openSession() async {
    if (_warehouseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Pick a warehouse.')));
      return;
    }
    setState(() => _submitting = true);
    try {
      await ref.read(posRepositoryProvider).openSession(
            warehouseId: _warehouseId!,
            openingCash: double.tryParse(_cashController.text) ?? 0,
          );
      ref.invalidate(currentSessionProvider);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final warehousesAsync = ref.watch(warehouseListProvider);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.point_of_sale, size: 56),
              const SizedBox(height: 16),
              Text(
                'Open a till session to start selling',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 24),
              warehousesAsync.when(
                loading: () => const LinearProgressIndicator(),
                error: (_, _) => const SizedBox.shrink(),
                data: (warehouses) => DropdownButtonFormField<String>(
                  initialValue: _warehouseId,
                  decoration: InputDecoration(labelText: l10n.warehouse),
                  items: warehouses.map((w) => DropdownMenuItem(value: w.id, child: Text(w.name))).toList(),
                  onChanged: (v) => setState(() => _warehouseId = v),
                ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _cashController,
                decoration: const InputDecoration(labelText: 'Opening cash float (ETB)'),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _submitting ? null : _openSession,
                child: _submitting
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Open Session'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
