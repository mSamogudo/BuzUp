import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/api_client.dart';
import 'core/providers.dart';
import 'core/theme.dart';
import 'features/auth/login_screen.dart';
import 'features/home/home_screen.dart';
import 'features/packages/packages_screen.dart';
import 'features/profile/profile_screen.dart';
import 'features/shell/main_shell.dart';
import 'features/splash/splash_screen.dart';
import 'features/tickets/buy_ticket_screen.dart';
import 'features/tickets/ticket_detail_screen.dart';
import 'features/tickets/tickets_list_screen.dart';
import 'features/packages/package_detail_screen.dart';
import 'features/profile/admin_fees_screen.dart';
import 'features/topup/topup_screen.dart';
import 'features/transactions/extract_screen.dart';
import 'features/transactions/transaction_detail_screen.dart';
import 'features/transactions/transactions_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(path: '/splash', builder: (_, _) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      // Modal full-screen routes that should NOT have the bottom nav.
      GoRoute(path: '/topup', builder: (_, _) => const TopupScreen()),
      GoRoute(path: '/tickets/buy', builder: (_, _) => const BuyTicketScreen()),
      GoRoute(
        path: '/tickets/:id',
        builder: (_, st) => TicketDetailScreen(
          ticketId: int.tryParse(st.pathParameters['id'] ?? '') ?? 0,
        ),
      ),
      GoRoute(path: '/extract', builder: (_, _) => const ExtractScreen()),
      GoRoute(path: '/admin-fees', builder: (_, _) => const AdminFeesScreen()),
      GoRoute(
        path: '/packages/active/:id',
        builder: (_, st) => ActivePackageDetailScreen(
          subscriptionId: int.tryParse(st.pathParameters['id'] ?? '') ?? 0,
        ),
      ),
      GoRoute(
        path: '/transactions/:id',
        builder: (_, st) => TransactionDetailScreen(
          txId: int.tryParse(st.pathParameters['id'] ?? '') ?? 0,
        ),
      ),
      // Main tabs wrapped in a shell with bottom navigation.
      ShellRoute(
        builder: (ctx, state, child) => MainShell(child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, _) => const HomeScreen()),
          GoRoute(path: '/tickets', builder: (_, _) => const TicketsListScreen()),
          GoRoute(path: '/packages', builder: (_, _) => const PackagesScreen()),
          GoRoute(path: '/transactions', builder: (_, _) => const TransactionsScreen()),
          GoRoute(path: '/profile', builder: (_, _) => const ProfileScreen()),
        ],
      ),
    ],
  );
});

class MobileApp extends ConsumerWidget {
  const MobileApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeControllerProvider);
    final locale = ref.watch(localeControllerProvider);
    ApiClient.onUnauthorized = () {
      try {
        router.go('/login');
      } catch (_) {/* router may not be ready */}
    };
    return MaterialApp.router(
      title: 'BuzUp Passageiro',
      debugShowCheckedModeBanner: false,
      theme: BuzUpTheme.light(),
      darkTheme: BuzUpTheme.dark(),
      themeMode: themeMode,
      locale: locale,
      supportedLocales: const [Locale('pt'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      routerConfig: router,
    );
  }
}
