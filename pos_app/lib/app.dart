import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/api_client.dart';
import 'core/device_gate.dart';
import 'core/device_info.dart';
import 'core/providers.dart';
import 'core/theme.dart';
import 'core/theme_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/cards/card_capture_screen.dart';
import 'features/cards/card_lookup_screen.dart';
import 'features/day_close/day_close_screen.dart';
import 'features/history/history_screen.dart';
import 'features/home/home_screen.dart';
import 'features/onboarding/activation_code_screen.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'features/passengers/passenger_onboard_screen.dart';
import 'features/passengers/passenger_recovery_screen.dart';
import 'features/sale/sale_flow_screen.dart';
import 'features/verify/verify_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const _SplashScreen()),
      GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingScreen()),
      GoRoute(path: '/activation-code', builder: (_, __) => const ActivationCodeScreen()),
      // Everything below requires the device to be ACTIVE on the portal.
      GoRoute(path: '/login', builder: (_, __) => const DeviceGate(child: LoginScreen())),
      GoRoute(path: '/home', builder: (_, __) => const DeviceGate(child: HomeScreen())),
      GoRoute(path: '/sale', builder: (_, __) => const DeviceGate(child: SaleFlowScreen())),
      GoRoute(path: '/verify', builder: (_, __) => const DeviceGate(child: VerifyScreen())),
      GoRoute(path: '/history', builder: (_, __) => const DeviceGate(child: HistoryScreen())),
      GoRoute(path: '/day-close', builder: (_, __) => const DeviceGate(child: DayCloseScreen())),
      GoRoute(path: '/cards', builder: (_, __) => const DeviceGate(child: CardLookupScreen())),
      GoRoute(path: '/cards/capture', builder: (_, __) => const DeviceGate(child: CardCaptureScreen())),
      GoRoute(path: '/passengers/onboard', builder: (_, __) => const DeviceGate(child: PassengerOnboardScreen())),
      GoRoute(path: '/passengers/recover', builder: (_, __) => const DeviceGate(child: PassengerRecoveryScreen())),
    ],
  );
});

/// Bootstraps the device every cold start:
///   1. Reads hardware fingerprint
///   2. Calls /api/agent/devices/self-onboard/  (idempotent)
///   3. Routes by returned device status:
///         active            -> /login (or /home if token saved)
///         pending_activation-> /activation-code
///         self_onboarded    -> /onboarding (waits for admin allocation)
///         anything else     -> /onboarding
class _SplashScreen extends ConsumerStatefulWidget {
  const _SplashScreen();

  @override
  ConsumerState<_SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<_SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(_route);
  }

  Future<void> _route() async {
    final store = ref.read(secureStoreProvider);
    final api = ref.read(agentApiProvider);

    String? serial;
    try {
      final fp = await readDeviceFingerprint();
      final res = await api.selfOnboard(
        serialNumber: fp.serialNumber,
        deviceType: fp.deviceType,
        modelName: fp.modelName,
        manufacturer: fp.manufacturer,
        androidId: fp.androidId,
        appVersion: '1.0.0',
        capabilities: const ['qr_scanner', 'camera'],
      );
      serial = res['serial_number'] as String?;
      if (serial != null) await store.saveDeviceSerial(serial);

      final status = (res['status'] as String?) ?? 'self_onboarded';
      final hasAgent = res['assigned_agent_id'] != null;

      if (!mounted) return;
      if (status == 'active') {
        final tok = await store.getAccess();
        context.go((tok == null || tok.isEmpty) ? '/login' : '/home');
      } else if (status == 'pending_activation' || hasAgent) {
        context.go('/activation-code');
      } else {
        context.go('/onboarding');
      }
    } catch (_) {
      // No network on startup: fall back to stored serial.
      final stored = await store.getDeviceSerial();
      if (!mounted) return;
      if (stored == null || stored.isEmpty) {
        context.go('/onboarding');
      } else {
        context.go('/login');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F1A35) : const Color(0xFFF7F4EE),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset(
              isDark ? 'assets/tpm_tur_dark.png' : 'assets/tpm_tur_light.png',
              height: 80,
              errorBuilder: (_, __, ___) => const SizedBox(height: 80),
            ),
            const SizedBox(height: 24),
            const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2, color: BuzUpColors.orange)),
          ],
        ),
      ),
    );
  }
}

class PosApp extends ConsumerWidget {
  const PosApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeControllerProvider);
    // Wire the 401 -> /login redirect via a static callback so any HTTP call
    // (regardless of which screen it originates from) drops the agent back
    // at the login screen when the JWT expires.
    ApiClient.onUnauthorized = () {
      try {
        router.go('/login');
      } catch (_) {/* router may not be ready during cold start */}
    };
    return MaterialApp.router(
      title: 'BuzUp POS',
      debugShowCheckedModeBanner: false,
      theme: BuzUpTheme.light(),
      darkTheme: BuzUpTheme.dark(),
      themeMode: themeMode,
      routerConfig: router,
    );
  }
}
