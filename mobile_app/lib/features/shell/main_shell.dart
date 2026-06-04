import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n.dart';
import '../../core/theme.dart';

/// Wraps the 5 main tabs (Home / Tickets / Packages / Transactions / Profile)
/// with a Material 3 NavigationBar. `go_router`'s ShellRoute hands us the
/// active route's widget via `child`.
class MainShell extends ConsumerWidget {
  const MainShell({super.key, required this.child});

  final Widget child;

  int _indexFor(String path) {
    if (path.startsWith('/tickets')) return 1;
    if (path.startsWith('/packages')) return 2;
    if (path.startsWith('/transactions')) return 3;
    if (path.startsWith('/profile')) return 4;
    return 0;
  }

  void _onSelect(BuildContext context, int idx) {
    switch (idx) {
      case 0: context.go('/home'); break;
      case 1: context.go('/tickets'); break;
      case 2: context.go('/packages'); break;
      case 3: context.go('/transactions'); break;
      case 4: context.go('/profile'); break;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tr = ref.watch(trProvider);
    final route = GoRouterState.of(context).uri.path;
    final idx = _indexFor(route);
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: idx,
        onDestinationSelected: (i) => _onSelect(context, i),
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        indicatorColor: BuzUpColors.orange.withValues(alpha: 0.18),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.home_outlined),
            selectedIcon: const Icon(Icons.home, color: BuzUpColors.orange),
            label: tr('nav.home'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.confirmation_number_outlined),
            selectedIcon: const Icon(Icons.confirmation_number, color: BuzUpColors.orange),
            label: tr('nav.tickets'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.card_giftcard_outlined),
            selectedIcon: const Icon(Icons.card_giftcard, color: BuzUpColors.orange),
            label: tr('nav.packages'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.receipt_long_outlined),
            selectedIcon: const Icon(Icons.receipt_long, color: BuzUpColors.orange),
            label: tr('nav.transactions'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.person_outline),
            selectedIcon: const Icon(Icons.person, color: BuzUpColors.orange),
            label: tr('nav.profile'),
          ),
        ],
      ),
    );
  }
}
