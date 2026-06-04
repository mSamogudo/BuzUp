import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/bus_loader.dart';
import '../../core/logger.dart';
import '../../core/providers.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _route();
  }

  Future<void> _route() async {
    await Future<void>.delayed(const Duration(milliseconds: 700));
    final tok = await ref.read(secureStoreProvider).getAccess();
    if (!mounted) return;
    final next = (tok == null || tok.isEmpty) ? '/login' : '/home';
    Log.info('splash -> $next');
    context.go(next);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Image.asset(
            isDark ? 'assets/tpm_tur_dark.png' : 'assets/tpm_tur_light.png',
            height: 80,
            errorBuilder: (_, _, _) => const SizedBox(height: 80),
          ),
          const SizedBox(height: 8),
          const Text('BuzUp Passageiro',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, letterSpacing: -0.4)),
          const SizedBox(height: 16),
          const BusLoader(size: 180, label: 'A iniciar...'),
        ]),
      ),
    );
  }
}
