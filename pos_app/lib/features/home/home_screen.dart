import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';

import '../../core/config.dart';
import '../../core/feedback.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';
import '../../core/theme_controller.dart';
import '../../core/transitions.dart';

/// Enterprise premium Home screen.
/// One accent (orange) for primary action, neutral grays for the rest.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  Timer? _heartbeatTimer;
  String? _deviceSerial;
  Map<String, dynamic>? _summary;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      _deviceSerial = await ref.read(secureStoreProvider).getDeviceSerial();
      _heartbeatTimer = Timer.periodic(AppConfig.heartbeatInterval, (_) => _sendHeartbeat());
      _sendHeartbeat();
      _loadSummary();
    });
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    super.dispose();
  }

  Future<void> _sendHeartbeat() async {
    try {
      double? lat;
      double? lng;
      if (Platform.isAndroid) {
        final perm = await Geolocator.checkPermission();
        if (perm == LocationPermission.always || perm == LocationPermission.whileInUse) {
          final pos = await Geolocator.getCurrentPosition(
            locationSettings: const LocationSettings(accuracy: LocationAccuracy.low),
          ).timeout(const Duration(seconds: 5), onTimeout: () => throw TimeoutException('gps'));
          lat = pos.latitude;
          lng = pos.longitude;
        }
      }
      await ref.read(agentApiProvider).heartbeat(
            serialNumber: _deviceSerial,
            latitude: lat,
            longitude: lng,
            appVersion: '1.0.0',
          );
    } catch (_) {}
  }

  Future<void> _loadSummary() async {
    try {
      final res = await ref.read(agentApiProvider).salesSummary();
      if (mounted) setState(() => _summary = res);
    } catch (_) {}
  }

  Future<bool> _confirmLogout(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Terminar Sessao?'),
        content: const Text('Pretende sair da app e voltar ao login?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('SAIR')),
        ],
      ),
    );
    return ok ?? false;
  }

  Future<void> _logout() async {
    final store = ref.read(secureStoreProvider);
    final refresh = await store.getRefresh();
    if (refresh != null) {
      try { await ref.read(agentApiProvider).logout(refresh); } catch (_) {}
    }
    final serial = await store.getDeviceSerial();
    await store.clearAll();
    if (serial != null) await store.saveDeviceSerial(serial);
    ref.invalidate(isLoggedInProvider);
    if (mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final meAsync = ref.watch(agentMeProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? const Color(0xFF0F1A35) : const Color(0xFFF7F4EE);
    final cardBg = isDark ? const Color(0xFF152444) : Colors.white;
    final txtMain = isDark ? Colors.white : BuzUpColors.navy;
    final txtMuted = txtMain.withValues(alpha: 0.6);
    final borderColor = isDark ? Colors.white12 : const Color(0xFFE5E0D5);

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final ok = await _confirmLogout(context);
        if (ok) await _logout();
      },
      child: Scaffold(
        backgroundColor: bg,
        body: SafeArea(
          child: meAsync.when(
            loading: () => _loadingState(),
            error: (e, _) => Center(child: Text('Erro: $e')),
            data: (me) {
              final agent = (me['agent'] as Map?) ?? {};
              return CustomScrollView(
                physics: const BouncingScrollPhysics(),
                slivers: [
                  // Top bar (custom, enterprise look)
                  SliverToBoxAdapter(
                    child: FadeIn(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(16, 12, 8, 0),
                        child: Row(children: [
                          Expanded(
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text('Bem-vindo,', style: TextStyle(color: txtMuted, fontSize: 12, fontWeight: FontWeight.w500)),
                              Text(
                                agent['full_name'] ?? '—',
                                style: TextStyle(color: txtMain, fontSize: 20, fontWeight: FontWeight.w700, letterSpacing: -0.3),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ]),
                          ),
                          IconButton(
                            iconSize: 22,
                            icon: Icon(_themeIcon(ref.watch(themeControllerProvider)), color: txtMuted),
                            onPressed: () => ref.read(themeControllerProvider.notifier).toggle(),
                          ),
                          IconButton(
                            iconSize: 22,
                            icon: Icon(Icons.logout, color: txtMuted),
                            onPressed: () async {
                              await AppFeedback.click();
                              if (await _confirmLogout(context)) await _logout();
                            },
                          ),
                        ]),
                      ),
                    ),
                  ),
                  // KPI strip
                  SliverToBoxAdapter(
                    child: FadeIn(
                      delay: const Duration(milliseconds: 80),
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
                        child: _kpiCard(cardBg, txtMain, txtMuted, borderColor),
                      ),
                    ),
                  ),
                  // Primary action
                  SliverToBoxAdapter(
                    child: FadeIn(
                      delay: const Duration(milliseconds: 160),
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
                        child: _primaryAction(
                          onTap: () async { AppFeedback.click(); await context.push('/sale'); _loadSummary(); },
                        ),
                      ),
                    ),
                  ),
                  // Secondary actions grid
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                    sliver: SliverGrid.count(
                      crossAxisCount: 2,
                      mainAxisSpacing: 10,
                      crossAxisSpacing: 10,
                      childAspectRatio: 1.6,
                      children: [
                        FadeIn(delay: const Duration(milliseconds: 200), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.nfc, 'TOP UP', () async { AppFeedback.click(); await context.push('/cards'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 210), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.person_add_alt, 'Novo passageiro', () async { AppFeedback.click(); await context.push('/passengers/onboard'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 220), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.replay, 'Recuperar cartao', () async { AppFeedback.click(); await context.push('/passengers/recover'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 240), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.qr_code_scanner, 'Validar bilhete', () async { AppFeedback.click(); await context.push('/verify'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 280), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.list_alt, 'Historico', () async { AppFeedback.click(); await context.push('/history'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 360), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.lock_clock, 'Fecho do dia', () async { AppFeedback.click(); await context.push('/day-close'); _loadSummary(); })),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _kpiCard(Color cardBg, Color txtMain, Color txtMuted, Color border) {
    final totals = _summary;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Receita de hoje', style: TextStyle(color: txtMuted, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.4)),
                const SizedBox(height: 6),
                totals == null
                    ? const Skeleton(height: 26, width: 140)
                    : Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
                        Text('${totals['total_revenue'] ?? '0.00'}',
                            style: TextStyle(color: txtMain, fontSize: 26, fontWeight: FontWeight.w800, letterSpacing: -0.5)),
                        const SizedBox(width: 6),
                        Text('MZN', style: TextStyle(color: txtMuted, fontSize: 12, fontWeight: FontWeight.w600)),
                      ]),
                const SizedBox(height: 2),
                Text(
                  totals == null ? '—'
                      : '${totals['confirmed_count'] ?? 0} vendas · ${totals['tickets_issued'] ?? 0} bilhetes',
                  style: TextStyle(color: txtMuted, fontSize: 11),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: BuzUpColors.orange.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.trending_up, color: BuzUpColors.orange, size: 22),
          ),
        ],
      ),
    );
  }

  Widget _primaryAction({required VoidCallback onTap}) {
    return Material(
      color: BuzUpColors.orange,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        splashColor: Colors.white.withValues(alpha: 0.15),
        highlightColor: Colors.white.withValues(alpha: 0.05),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFFE47B11), Color(0xFFF59E3D)],
            ),
            boxShadow: [
              BoxShadow(color: BuzUpColors.orange.withValues(alpha: 0.35), blurRadius: 14, offset: const Offset(0, 6)),
            ],
          ),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(10)),
              child: const Icon(Icons.confirmation_number_outlined, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 14),
            const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('NOVA VENDA', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w800, letterSpacing: 1.2)),
              SizedBox(height: 2),
              Text('Emitir bilhete electronico', style: TextStyle(color: Colors.white70, fontSize: 11)),
            ])),
            const Icon(Icons.arrow_forward, color: Colors.white, size: 20),
          ]),
        ),
      ),
    );
  }

  Widget _tile(Color cardBg, Color txtMain, Color txtMuted, Color border, IconData icon, String label, VoidCallback onTap) {
    return Material(
      color: cardBg,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: txtMain.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, size: 18, color: txtMain),
              ),
              Text(label, style: TextStyle(color: txtMain, fontSize: 13, fontWeight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _loadingState() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: const [
        SizedBox(height: 12),
        Skeleton(height: 22, width: 120),
        SizedBox(height: 6),
        Skeleton(height: 24, width: 220),
        SizedBox(height: 20),
        Skeleton(height: 92, radius: 14),
        SizedBox(height: 12),
        Skeleton(height: 76, radius: 14),
        SizedBox(height: 12),
        Row(children: [Expanded(child: Skeleton(height: 88, radius: 12)), SizedBox(width: 10), Expanded(child: Skeleton(height: 88, radius: 12))]),
        SizedBox(height: 10),
        Row(children: [Expanded(child: Skeleton(height: 88, radius: 12)), SizedBox(width: 10), Expanded(child: Skeleton(height: 88, radius: 12))]),
      ]),
    );
  }

  IconData _themeIcon(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.light: return Icons.light_mode_outlined;
      case ThemeMode.dark: return Icons.dark_mode_outlined;
      case ThemeMode.system: return Icons.brightness_auto_outlined;
    }
  }
}
