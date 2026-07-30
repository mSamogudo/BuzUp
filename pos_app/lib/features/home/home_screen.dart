import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_version.dart';
import '../../core/app_update.dart';
import '../../core/config.dart';
import '../../core/feedback.dart';
import '../../core/location.dart';
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
  LocationReadiness _location = LocationReadiness.ok;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      _deviceSerial = await ref.read(secureStoreProvider).getDeviceSerial();
      // Pedido explicito antes do primeiro heartbeat: sem isto o Android
      // mantem a permissao em "denied" para sempre e o autocarro nunca chega
      // ao mapa dos passageiros.
      await _ensureLocation();
      _heartbeatTimer = Timer.periodic(AppConfig.heartbeatInterval, (_) => _sendHeartbeat());
      _sendHeartbeat();
      _loadSummary();
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) checkForAppUpdate(context, ref);
    });
  }

  @override
  void dispose() {
    _heartbeatTimer?.cancel();
    super.dispose();
  }

  /// Garante permissao de localizacao e guarda o estado para o aviso do ecra.
  Future<void> _ensureLocation() async {
    final readiness = await DeviceLocation.ensurePermission();
    if (mounted) setState(() => _location = readiness);
  }

  Future<void> _sendHeartbeat() async {
    try {
      final pos = await DeviceLocation.current();
      await ref.read(agentApiProvider).heartbeat(
            serialNumber: _deviceSerial,
            latitude: pos?.latitude,
            longitude: pos?.longitude,
            // Alimenta a seta/velocidade do autocarro no mapa dos passageiros.
            speedKmh: (pos != null && pos.speed >= 0) ? pos.speed * 3.6 : null,
            heading: (pos != null && pos.heading >= 0) ? pos.heading : null,
            appVersion: AppVersion.version,
          );
      // O GPS pode ter sido desligado depois do arranque; mantem o aviso fiel.
      if (mounted && pos == null && _location == LocationReadiness.ok) {
        setState(() => _location = LocationReadiness.serviceOff);
      } else if (mounted && pos != null && _location != LocationReadiness.ok) {
        setState(() => _location = LocationReadiness.ok);
      }
    } catch (_) {}
  }

  /// Aviso discreto mas accionavel: diz o que falha e leva ao sitio certo
  /// para corrigir, em vez de deixar o agente sem saber que nao e seguido.
  Widget _locationBanner() {
    const amber = Color(0xFFB45309);
    final canRetry = _location == LocationReadiness.denied;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
      decoration: BoxDecoration(
        color: amber.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: amber.withValues(alpha: 0.35)),
      ),
      child: Row(children: [
        const Icon(Icons.location_off, color: amber, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            DeviceLocation.describe(_location),
            style: const TextStyle(color: amber, fontSize: 12, fontWeight: FontWeight.w600, height: 1.3),
          ),
        ),
        TextButton(
          onPressed: () async {
            await AppFeedback.click();
            if (canRetry) {
              await _ensureLocation();
            } else {
              await DeviceLocation.openSettingsFor(_location);
              // O operador volta das definicoes: reavalia sem obrigar a
              // reiniciar a aplicacao.
              await _ensureLocation();
            }
          },
          child: Text(canRetry ? 'Permitir' : 'Definicoes',
              style: const TextStyle(color: amber, fontWeight: FontWeight.w700)),
        ),
      ]),
    );
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
              return RefreshIndicator(
                // Arrastar para actualizar tem de refazer o perfil E os KPIs.
                // Antes nao existia aqui: o nome e a receita do dia ficavam
                // presos ao primeiro carregamento e a unica saida era sair da
                // app. `ref.refresh(...).future` espera mesmo pelos dados —
                // `invalidate` devolvia logo e o indicador desaparecia antes.
                onRefresh: () async {
                  await Future.wait([
                    ref.refresh(agentMeProvider.future),
                    _loadSummary(),
                  ]);
                },
                child: CustomScrollView(
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
                            tooltip: 'Perfil',
                            icon: Icon(Icons.account_circle_outlined, color: txtMuted),
                            onPressed: () async {
                              await AppFeedback.click();
                              if (context.mounted) await context.push('/profile');
                            },
                          ),
                        ]),
                      ),
                    ),
                  ),
                  // Sem localizacao o autocarro desaparece do mapa dos
                  // passageiros sem qualquer erro. O agente tem de saber.
                  if (_location != LocationReadiness.ok)
                    SliverToBoxAdapter(
                      child: FadeIn(
                        delay: const Duration(milliseconds: 60),
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
                          child: _locationBanner(),
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
                  // Cartao da viagem do motorista (so para quem tem o perfil)
                  if (me['driver'] != null)
                    SliverToBoxAdapter(
                      child: FadeIn(
                        delay: const Duration(milliseconds: 120),
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
                          child: _driverTripCard(cardBg, txtMain, txtMuted, borderColor),
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
                  // Secondary actions grid — 3 colunas e cartoes mais baixos.
                  // Com 2 colunas a 1.6, as 7 accoes ocupavam 4 linhas e a
                  // ultima ficava fora do ecra num terminal de 5"; assim
                  // cabem em 3 linhas sem rolagem.
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
                    sliver: SliverGrid.count(
                      crossAxisCount: 3,
                      mainAxisSpacing: 8,
                      crossAxisSpacing: 8,
                      childAspectRatio: 1.02,
                      children: [
                        FadeIn(delay: const Duration(milliseconds: 200), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.nfc, 'TOP UP', () async { AppFeedback.click(); await context.push('/cards'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 210), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.person_add_alt, 'Novo passageiro', () async { AppFeedback.click(); await context.push('/passengers/onboard'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 220), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.replay, 'Recuperar cartao', () async { AppFeedback.click(); await context.push('/passengers/recover'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 240), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.qr_code_scanner, 'Validar bilhete', () async { AppFeedback.click(); await context.push('/verify'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 280), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.list_alt, 'Historico', () async { AppFeedback.click(); await context.push('/history'); _loadSummary(); })),
                        FadeIn(delay: const Duration(milliseconds: 360), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.lock_clock, 'Fecho do dia', () async { AppFeedback.click(); await context.push('/day-close'); _loadSummary(); })),
                        if (me['driver'] != null)
                          FadeIn(delay: const Duration(milliseconds: 400), child: _tile(cardBg, txtMain, txtMuted, borderColor, Icons.departure_board, 'Minhas viagens', () async { AppFeedback.click(); await context.push('/driver/trips'); _loadSummary(); })),
                      ],
                    ),
                  ),
                ],
                ),
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

  /// Cartao "viagem em mao" do motorista: mostra a viagem activa (ou a
  /// proxima) e leva ao ecra de viagens. As accoes vivem la — aqui e so o
  /// estado, sempre visivel mal se entra na app.
  Widget _driverTripCard(Color cardBg, Color txtMain, Color txtMuted, Color border) {
    final activeAsync = ref.watch(activeDriverTripProvider);
    final nextAsync = ref.watch(nextDriverTripProvider);

    final active = activeAsync.valueOrNull;
    final next = nextAsync.valueOrNull;
    final trip = active ?? next;

    String subtitle;
    Color accent;
    if (activeAsync.isLoading) {
      subtitle = 'A carregar viagens...';
      accent = BuzUpColors.blue;
    } else if (active != null) {
      subtitle = active['status'] == 'paused' ? 'Viagem pausada' : 'Viagem em curso';
      accent = BuzUpColors.success;
    } else if (next != null) {
      final dep = DateTime.tryParse((next['planned_departure_at'] ?? '').toString())?.toLocal();
      subtitle = dep == null
          ? 'Proxima viagem'
          : 'Proxima partida ${dep.hour.toString().padLeft(2, '0')}:${dep.minute.toString().padLeft(2, '0')}';
      accent = BuzUpColors.blue;
    } else {
      subtitle = 'Sem viagens alocadas';
      accent = BuzUpColors.blue;
    }

    return Material(
      color: cardBg,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () async {
          AppFeedback.click();
          await context.push('/driver/trips');
          ref.invalidate(driverTripsProvider);
        },
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: active != null ? accent.withValues(alpha: 0.55) : border),
          ),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(Icons.directions_bus, color: accent, size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(subtitle, style: TextStyle(color: txtMuted, fontSize: 11, fontWeight: FontWeight.w600)),
                const SizedBox(height: 2),
                Text(
                  trip == null ? 'Minhas viagens' : '${trip['route_code'] ?? ''} · ${trip['route_name'] ?? ''}',
                  style: TextStyle(color: txtMain, fontSize: 15, fontWeight: FontWeight.w800, letterSpacing: -0.2),
                  overflow: TextOverflow.ellipsis,
                ),
              ]),
            ),
            Icon(Icons.arrow_forward, color: txtMuted, size: 20),
          ]),
        ),
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
              colors: [Color(0xFF1D5FA7), Color(0xFF2D8CF0)],
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
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: border),
          ),
          // Centrado e em coluna: em 3 colunas o cartao fica quadrado, e
          // alinhar o icone acima do texto le-se melhor do que espalha-los
          // pelos cantos.
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(7),
                decoration: BoxDecoration(
                  color: txtMain.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, size: 18, color: txtMain),
              ),
              const SizedBox(height: 6),
              Text(
                label,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: txtMain, fontSize: 11.5, fontWeight: FontWeight.w600, height: 1.15),
              ),
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
