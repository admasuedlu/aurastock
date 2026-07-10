import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/accounting/presentation/accounting_screen.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/signup_screen.dart';
import '../../features/auth/presentation/splash_screen.dart';
import '../../features/auth/providers/auth_controller.dart';
import '../../features/dashboard/presentation/dashboard_screen.dart';
import '../../features/insights/presentation/insights_screen.dart';
import '../../features/inventory/presentation/inventory_screen.dart';
import '../../features/notifications/presentation/notifications_screen.dart';
import '../../features/platform/presentation/platform_screen.dart';
import '../../features/portal/presentation/portal_home_screen.dart';
import '../../features/portal/presentation/portal_login_screen.dart';
import '../../features/portal/providers/portal_providers.dart';
import '../../features/pos/presentation/pos_screen.dart';
import '../../features/products/presentation/product_list_screen.dart';
import '../../features/purchasing/presentation/purchasing_screen.dart';
import '../../features/reports/presentation/reports_screen.dart';
import '../../features/sales/presentation/sales_screen.dart';
import '../../features/settings/presentation/settings_screen.dart';
import '../../features/shell/presentation/app_shell.dart';

class _RouterRefreshNotifier extends ChangeNotifier {
  _RouterRefreshNotifier(Ref ref) {
    ref.listen(authControllerProvider, (previous, next) => notifyListeners());
    ref.listen(portalSessionControllerProvider, (previous, next) => notifyListeners());
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final refreshNotifier = _RouterRefreshNotifier(ref);
  ref.onDispose(refreshNotifier.dispose);

  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: refreshNotifier,
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      final portalState = ref.read(portalSessionControllerProvider);
      final location = state.matchedLocation;
      // The portal login is an auth route too: reachable from the staff login
      // link before anyone is signed in.
      final isAuthRoute =
          location == '/login' || location == '/signup' || location == '/portal-login';
      final isSplash = location == '/splash';

      if (authState.isLoading || portalState.isLoading) {
        return isSplash ? null : '/splash';
      }

      // A portal session takes over the app entirely (like platform staff):
      // an external customer/supplier only ever sees the portal home.
      final portalSession = portalState.valueOrNull;
      if (portalSession != null) {
        return location == '/portal-home' ? null : '/portal-home';
      }

      final user = authState.valueOrNull;
      if (user == null) {
        return isAuthRoute ? null : '/login';
      }
      // Platform staff (no company) get the platform-admin shell and nothing
      // else; tenant users can never reach it.
      final isPlatformStaff = user.companyId == null;
      if (isPlatformStaff) {
        return location == '/platform' ? null : '/platform';
      }
      if (isAuthRoute || isSplash || location == '/platform' || location == '/portal-home') {
        return '/';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/signup', builder: (context, state) => const SignupScreen()),
      GoRoute(path: '/platform', builder: (context, state) => const PlatformScreen()),
      GoRoute(path: '/portal-login', builder: (context, state) => const PortalLoginScreen()),
      GoRoute(path: '/portal-home', builder: (context, state) => const PortalHomeScreen()),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(path: '/', builder: (context, state) => const DashboardScreen()),
          GoRoute(path: '/pos', builder: (context, state) => const PosScreen()),
          GoRoute(path: '/products', builder: (context, state) => const ProductListScreen()),
          GoRoute(path: '/inventory', builder: (context, state) => const InventoryScreen()),
          GoRoute(path: '/sales', builder: (context, state) => const SalesScreen()),
          GoRoute(path: '/purchases', builder: (context, state) => const PurchasingScreen()),
          GoRoute(path: '/accounting', builder: (context, state) => const AccountingScreen()),
          GoRoute(path: '/reports', builder: (context, state) => const ReportsScreen()),
          GoRoute(path: '/insights', builder: (context, state) => const InsightsScreen()),
          GoRoute(path: '/notifications', builder: (context, state) => const NotificationsScreen()),
          GoRoute(path: '/settings', builder: (context, state) => const SettingsScreen()),
        ],
      ),
    ],
  );
});
