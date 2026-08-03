import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/app_update.dart';
import '../../core/bus_loader.dart';
import '../../core/config.dart';
import '../../core/i18n.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  String? _accessToken;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      final tok = await ref.read(secureStoreProvider).getAccess();
      if (mounted) setState(() => _accessToken = tok);
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) checkForAppUpdate(context, ref);
    });
  }

  String _money(dynamic v) {
    final n = double.tryParse('${v ?? 0}') ?? 0;
    return NumberFormat('#,##0.00', 'pt_PT').format(n);
  }

  @override
  Widget build(BuildContext context) {
    final me = ref.watch(meProvider);
    final tr = ref.watch(trProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('nav.home'), style: const TextStyle(fontWeight: FontWeight.w800)),
        actions: [
          IconButton(
            tooltip: tr('common.refresh'),
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(meProvider),
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async => ref.invalidate(meProvider),
          child: me.when(
            loading: () => Center(child: BusLoader(size: 200, label: tr('home.loadingWallet'))),
            error: (e, _) => ListView(children: [
              Padding(
                padding: const EdgeInsets.all(20),
                child: Text('${tr('common.error')}: $e', style: const TextStyle(color: BuzUpColors.danger)),
              ),
            ]),
            data: (data) => _content(data, tr),
          ),
        ),
      ),
    );
  }

  Widget _content(Map<String, dynamic> data, dynamic tr) {
    final fullName = (data['full_name'] as String?) ?? '-';
    final balance = data['balance'];
    final cardNumber = data['card_number'] as String?;
    final cardId = data['card_id'] as int?;
    final activePackages = (data['active_packages'] as List?) ?? const [];

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      children: [
        Text('${tr('home.hello')}, ${fullName.split(' ').first}',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: -0.3)),
        const SizedBox(height: 12),
        _balanceCard(balance, tr),
        const SizedBox(height: 14),
        if (cardNumber != null && cardId != null && _accessToken != null)
          _qrCard(cardNumber, cardId, _accessToken!, tr),
        const SizedBox(height: 14),
        _quickActions(tr),
        const SizedBox(height: 14),
        _packagesSection(activePackages, tr),
      ],
    );
  }

  Widget _balanceCard(dynamic balance, dynamic tr) {
    final visible = ref.watch(balanceVisibleProvider);
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 16, 16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1D5FA7), Color(0xFF2D8CF0)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(color: BuzUpColors.orange.withValues(alpha: 0.32),
              blurRadius: 22, offset: const Offset(0, 8)),
        ],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: Text(tr('home.balanceLabel'),
                style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 11,
                    letterSpacing: 1.6,
                    fontWeight: FontWeight.w700)),
          ),
          InkWell(
            onTap: () => ref.read(balanceVisibleProvider.notifier).toggle(),
            borderRadius: BorderRadius.circular(20),
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Icon(
                visible ? Icons.visibility_off : Icons.visibility,
                color: Colors.white,
                size: 20,
              ),
            ),
          ),
        ]),
        const SizedBox(height: 4),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 220),
          transitionBuilder: (child, anim) =>
              FadeTransition(opacity: anim, child: child),
          child: Row(
            key: ValueKey(visible),
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(visible ? _money(balance) : '•••••',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 34,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.4)),
              const SizedBox(width: 6),
              Text(tr('currency.mzn'),
                  style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 13,
                      fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ]),
    );
  }

  Widget _qrCard(String cardNumber, int cardId, String token, dynamic tr) {
    // O QR sempre aberto ocupava ~250px e empurrava as accoes rapidas para
    // fora do ecra. Fica um cartao compacto; tocar abre o QR em grande num
    // dialogo — que e tambem quando ele e preciso, na hora de mostrar ao
    // agente.
    final surface = Theme.of(context).colorScheme.surface;
    final outline = Theme.of(context).colorScheme.outline;
    final muted = Theme.of(context).brightness == Brightness.dark
        ? BuzUpColors.mutedDark : BuzUpColors.muted;
    return Material(
      color: surface,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: () => _showQrDialog(cardNumber, cardId, token, tr),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: outline),
          ),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: BuzUpColors.blue.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.qr_code_2, size: 26, color: BuzUpColors.blue),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${tr('home.cardPrefix')} $cardNumber',
                    style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
                Text(tr('home.showAgent'),
                    style: TextStyle(fontSize: 11.5, color: muted, fontWeight: FontWeight.w600)),
              ]),
            ),
            const Icon(Icons.chevron_right, color: BuzUpColors.mutedDark),
          ]),
        ),
      ),
    );
  }

  void _showQrDialog(String cardNumber, int cardId, String token, dynamic tr) {
    // O token vai no cabecalho, nao no URL: um URL com o token de acesso ficava
    // gravado no log do servidor. De caminho, o URL passa a ser estavel, por
    // isso a cache da imagem deixa de ser invalidada a cada renovacao de token.
    final url = '${AppConfig.apiBaseUrl}/api/cards/$cardId/qr.png';
    showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 14),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(tr('home.showAgent'),
                style: const TextStyle(
                    fontSize: 11, letterSpacing: 1.6,
                    fontWeight: FontWeight.w800, color: BuzUpColors.muted)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFE4EBF3)),
              ),
              child: CachedNetworkImage(
                imageUrl: url,
                httpHeaders: {'Authorization': 'Bearer $token'},
                width: 260, height: 260,
                fit: BoxFit.contain,
                placeholder: (_, _) => const SizedBox(
                  width: 260, height: 260,
                  child: Center(child: BusLoader(size: 110, label: '')),
                ),
                errorWidget: (_, _, _) => const SizedBox(
                  width: 260, height: 260,
                  child: Center(child: Icon(Icons.qr_code_2, size: 90, color: BuzUpColors.muted)),
                ),
              ),
            ),
            const SizedBox(height: 10),
            Text('${tr('home.cardPrefix')} $cardNumber',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Fechar'),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _quickActions(dynamic tr) {
    return Column(children: [
      // Primary CTA: full-width gradient "Buy ticket" so the most common
      // passenger action is obvious instead of hidden in a corner.
      InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => context.push('/tickets/buy'),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF1D5FA7), Color(0xFF2D8CF0)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(color: BuzUpColors.orange.withValues(alpha: 0.30),
                  blurRadius: 14, offset: const Offset(0, 6)),
            ],
          ),
          child: Row(children: [
            const Icon(Icons.confirmation_number, color: Colors.white, size: 22),
            const SizedBox(width: 10),
            Expanded(
              child: Text(tr('home.buyTicket'),
                  style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w900, letterSpacing: 0.6)),
            ),
            const Icon(Icons.arrow_forward, color: Colors.white, size: 20),
          ]),
        ),
      ),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: _action(Icons.add, tr('home.topup'), () async {
          await context.push('/topup');
          ref.invalidate(meProvider);
        })),
        const SizedBox(width: 10),
        Expanded(child: _action(Icons.card_giftcard, tr('home.packages'), () {
          context.go('/packages');
        })),
        const SizedBox(width: 10),
        Expanded(child: _action(Icons.history, tr('home.transactions'), () {
          context.go('/transactions');
        })),
      ]),
    ]);
  }

  String _packageSummary(Map p) {
    final discountType = (p['discount_type'] ?? '').toString();
    final special = double.tryParse('${p['special_balance'] ?? 0}') ?? 0;
    final trips = p['trips_remaining'] as int? ?? 0;
    final expires = (p['expires_at'] ?? '').toString().split('T').first;
    final summary = switch (discountType) {
      'fixed_amount' => 'Saldo especial: ${special.toStringAsFixed(2)} MZN',
      'free_trips' => '$trips viagens restantes',
      'percentage' => 'Desconto ${p['discount_value']?.toString() ?? '0'}%',
      _ => 'Activo',
    };
    return '$summary · expira $expires';
  }

  Widget _action(IconData icon, String label, VoidCallback onTap) {
    final surface = Theme.of(context).colorScheme.surface;
    final outline = Theme.of(context).colorScheme.outline;
    return Material(
      color: surface,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
          decoration: BoxDecoration(
            border: Border.all(color: outline),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, color: BuzUpColors.orange, size: 22),
            const SizedBox(height: 4),
            Text(label,
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700)),
          ]),
        ),
      ),
    );
  }

  Widget _packagesSection(List<dynamic> packages, dynamic tr) {
    final surface = Theme.of(context).colorScheme.surface;
    final outline = Theme.of(context).colorScheme.outline;
    final muted = Theme.of(context).brightness == Brightness.dark
        ? BuzUpColors.mutedDark : BuzUpColors.muted;
    if (packages.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: outline),
        ),
        child: Row(children: [
          Icon(Icons.card_giftcard, color: muted),
          const SizedBox(width: 10),
          Expanded(child: Text(tr('home.noPackages'),
              style: TextStyle(fontSize: 12.5, color: muted))),
        ]),
      );
    }
    return Column(children: [
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Align(
          alignment: Alignment.centerLeft,
          child: Text(tr('home.activePackages'),
              style: TextStyle(fontSize: 11, letterSpacing: 1.4, color: muted, fontWeight: FontWeight.w700)),
        ),
      ),
      const SizedBox(height: 6),
      for (final p in packages.cast<Map>())
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Material(
            color: surface,
            borderRadius: BorderRadius.circular(14),
            child: InkWell(
              borderRadius: BorderRadius.circular(14),
              onTap: () {
                final id = p['id'] as int?;
                if (id != null) context.push('/packages/active/$id');
              },
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: outline),
                ),
                child: Row(children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: BuzUpColors.orange.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.card_giftcard, color: BuzUpColors.orange),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                      Text(p['package_name']?.toString() ?? '-',
                          style: const TextStyle(fontWeight: FontWeight.w800)),
                      const SizedBox(height: 2),
                      Text(_packageSummary(p),
                          style: const TextStyle(fontSize: 11.5, color: BuzUpColors.muted)),
                    ]),
                  ),
                  const Icon(Icons.chevron_right, color: BuzUpColors.muted),
                ]),
              ),
            ),
          ),
        ),
    ]);
  }
}
