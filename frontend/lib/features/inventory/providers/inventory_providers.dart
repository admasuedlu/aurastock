import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/inventory_repository.dart';
import '../domain/inventory_models.dart';

final inventoryRepositoryProvider = Provider<InventoryRepository>((ref) {
  return InventoryRepository(ref.watch(apiClientProvider).dio);
});

final warehouseListProvider = FutureProvider.autoDispose<List<Warehouse>>((ref) {
  return ref.watch(inventoryRepositoryProvider).fetchWarehouses();
});

final stockItemListProvider = FutureProvider.autoDispose<List<StockItem>>((ref) {
  return ref.watch(inventoryRepositoryProvider).fetchStockItems();
});

final lowStockItemListProvider = FutureProvider.autoDispose<List<StockItem>>((ref) {
  return ref.watch(inventoryRepositoryProvider).fetchStockItems(lowStockOnly: true);
});

final movementListProvider = FutureProvider.autoDispose<List<StockMovement>>((ref) {
  return ref.watch(inventoryRepositoryProvider).fetchMovements();
});
