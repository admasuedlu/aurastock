import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers/core_providers.dart';
import '../data/pos_repository.dart';
import '../domain/pos_models.dart';

final posRepositoryProvider = Provider<PosRepository>((ref) {
  return PosRepository(ref.watch(apiClientProvider).dio);
});

final currentSessionProvider = FutureProvider.autoDispose<PosSession?>((ref) {
  return ref.watch(posRepositoryProvider).fetchCurrentSession();
});

final sessionTransactionsProvider = FutureProvider.autoDispose.family<List<PosTransaction>, String>((ref, sessionId) {
  return ref.watch(posRepositoryProvider).fetchTransactions(sessionId);
});

class CartItem {
  CartItem({
    required this.productId,
    required this.productName,
    required this.sku,
    required this.unitPrice,
    required this.taxPercent,
    this.quantity = 1,
  });

  final String productId;
  final String productName;
  final String sku;
  final double unitPrice;
  final double taxPercent;
  int quantity;

  double get lineTotal => unitPrice * quantity * (1 + taxPercent / 100);
}

class CartController extends Notifier<List<CartItem>> {
  @override
  List<CartItem> build() => [];

  void addProduct({
    required String productId,
    required String productName,
    required String sku,
    required double unitPrice,
    required double taxPercent,
  }) {
    final index = state.indexWhere((item) => item.productId == productId);
    if (index != -1) {
      state[index].quantity += 1;
      state = [...state];
    } else {
      state = [
        ...state,
        CartItem(productId: productId, productName: productName, sku: sku, unitPrice: unitPrice, taxPercent: taxPercent),
      ];
    }
  }

  void updateQuantity(String productId, int quantity) {
    if (quantity <= 0) {
      removeProduct(productId);
      return;
    }
    final index = state.indexWhere((item) => item.productId == productId);
    if (index == -1) return;
    state[index].quantity = quantity;
    state = [...state];
  }

  void removeProduct(String productId) {
    state = state.where((item) => item.productId != productId).toList();
  }

  void clear() => state = [];

  double get subtotal => state.fold(0, (sum, item) => sum + item.unitPrice * item.quantity);
  double get taxTotal => state.fold(0, (sum, item) => sum + item.unitPrice * item.quantity * item.taxPercent / 100);
  double get total => subtotal + taxTotal;
}

final cartControllerProvider = NotifierProvider<CartController, List<CartItem>>(CartController.new);
