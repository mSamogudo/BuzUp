import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/bus_loader.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// Detail view for an *active* subscription (PassengerPackage), driven by
/// data already in meProvider — no extra fetch needed. Shows discount type,
/// remaining balance/trips, expiry countdown, routes restriction list and
/// trips used so the passenger understands exactly what they have.
class ActivePackageDetailScreen extends ConsumerWidget {
  const ActivePackageDetailScreen({super.key, required this.subscriptionId});

  final int subscriptionId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalhes do pacote'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/home'),
        ),
      ),
      body: SafeArea(
        child: me.when(
          loading: () => const Center(child: BusLoader(label: 'A carregar pacote...')),
          error: (e, _) => Center(child: Text('Erro: $e',
              style: const TextStyle(color: BuzUpColors.danger))),
          data: (data) {
            final list = (data['active_packages'] as List?)?.cast<Map>() ?? const [];
            final pkg = list.firstWhere(
              (p) => p['id'] == subscriptionId,
              orElse: () => const {},
            );
            if (pkg.isEmpty) {
              return const Center(
                child: Text('Pacote nao encontrado.',
                    style: TextStyle(color: BuzUpColors.muted)),
              );
            }
            return _content(context, pkg.cast<String, dynamic>());
          },
        ),
      ),
    );
  }

  Widget _content(BuildContext context, Map<String, dynamic> pkg) {
    final name = (pkg['package_name'] ?? '-').toString();
    final description = (pkg['package_description'] ?? '').toString();
    final discountType = (pkg['discount_type'] ?? '').toString();
    final discountValue = (pkg['discount_value'] ?? '0').toString();
    final specialBalance = double.tryParse('${pkg['special_balance'] ?? 0}') ?? 0;
    final tripsRemaining = pkg['trips_remaining'] as int? ?? 0;
    final tripsUsed = pkg['trips_used'] as int? ?? 0;
    final maxTrips = pkg['max_trips'] as int? ?? 0;
    final price = double.tryParse('${pkg['package_price'] ?? 0}') ?? 0;
    final expiresAtIso = pkg['expires_at']?.toString();
    final activatedAtIso = pkg['activated_at']?.toString();
    final routes = (pkg['routes'] as List?)?.cast<Map>() ?? const [];
    final status = (pkg['status'] ?? 'active').toString();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        _hero(name, description, status, discountType, discountValue),
        const SizedBox(height: 14),
        _statusCards(context, discountType, discountValue, specialBalance, tripsRemaining, tripsUsed, maxTrips),
        const SizedBox(height: 14),
        _section(context, 'Validade', [
          _row(Icons.event_available, 'Activado em', _fmt(activatedAtIso ?? '')),
          _row(Icons.event_busy, 'Expira em', _fmt(expiresAtIso ?? '')),
          _row(Icons.schedule, 'Dias restantes', _daysLeftLabel(expiresAtIso)),
        ]),
        const SizedBox(height: 14),
        _section(context, 'Preco pago', [
          _row(Icons.payments, 'Valor', '${_money(price)} MZN'),
        ]),
        if (routes.isNotEmpty) ...[
          const SizedBox(height: 14),
          _section(context, 'Rotas permitidas',
              routes.map((r) => _row(Icons.route, r['route_code']?.toString() ?? '-',
                  r['route_name']?.toString() ?? '-')).toList()),
        ] else ...[
          const SizedBox(height: 14),
          _section(context, 'Rotas', [
            _row(Icons.public, 'Aplicacao', 'Todas as rotas'),
          ]),
        ],
      ],
    );
  }

  Widget _hero(String name, String description, String status, String discountType, String discountValue) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [BuzUpColors.navy, Color(0xFF13316E)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.card_giftcard, color: BuzUpColors.orange, size: 24),
          const SizedBox(width: 8),
          Expanded(
            child: Text(name,
                style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
          ),
          _statusPill(status),
        ]),
        if (description.isNotEmpty) Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(description,
              style: const TextStyle(color: Colors.white70, fontSize: 12.5, fontWeight: FontWeight.w600)),
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(_discountTypeLabel(discountType, discountValue),
              style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800, letterSpacing: 0.3)),
        ),
      ]),
    );
  }

  Widget _statusCards(BuildContext context, String discountType, String discountValue, double balance, int tripsRemaining, int tripsUsed, int maxTrips) {
    if (discountType == 'fixed_amount') {
      return _bigCard('SALDO ESPECIAL DISPONIVEL', '${_money(balance)} MZN',
          'Aplicado primeiro em cada viagem ate esgotar.',
          color: BuzUpColors.success);
    }
    if (discountType == 'free_trips') {
      final pctUsed = maxTrips > 0 ? tripsUsed / maxTrips : 0.0;
      return Container(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Theme.of(context).colorScheme.outline),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('VIAGENS DISPONIVEIS',
              style: TextStyle(fontSize: 10.5, letterSpacing: 1.5, color: BuzUpColors.muted, fontWeight: FontWeight.w900)),
          const SizedBox(height: 4),
          Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
            Text('$tripsRemaining',
                style: const TextStyle(fontSize: 38, fontWeight: FontWeight.w900, color: BuzUpColors.success)),
            const SizedBox(width: 4),
            Text(' / $maxTrips',
                style: const TextStyle(fontSize: 16, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: pctUsed.clamp(0, 1),
              minHeight: 10,
              backgroundColor: BuzUpColors.border,
              valueColor: const AlwaysStoppedAnimation(BuzUpColors.success),
            ),
          ),
          const SizedBox(height: 6),
          Text('$tripsUsed viagens usadas, $tripsRemaining restantes',
              style: const TextStyle(fontSize: 11.5, color: BuzUpColors.muted)),
        ]),
      );
    }
    return _bigCard(
      'DESCONTO ACTIVO',
      '$discountValue %',
      'Aplicado sobre o valor da tarifa em cada viagem.',
      color: BuzUpColors.orange,
    );
  }

  Widget _bigCard(String label, String value, String subtitle, {required Color color}) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label,
            style: TextStyle(fontSize: 10.5, letterSpacing: 1.5, color: color, fontWeight: FontWeight.w900)),
        const SizedBox(height: 4),
        Text(value,
            style: TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: color, letterSpacing: -0.4)),
        const SizedBox(height: 4),
        Text(subtitle, style: const TextStyle(fontSize: 11.5, color: BuzUpColors.muted)),
      ]),
    );
  }

  Widget _section(BuildContext context, String title, List<Widget> rows) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
          child: Text(title.toUpperCase(),
              style: const TextStyle(fontSize: 10.5, color: BuzUpColors.muted,
                  fontWeight: FontWeight.w800, letterSpacing: 1.4)),
        ),
        for (int i = 0; i < rows.length; i++) ...[
          rows[i],
          if (i < rows.length - 1) const Divider(height: 1),
        ],
      ]),
    );
  }

  Widget _row(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(children: [
        Icon(icon, size: 17, color: BuzUpColors.muted),
        const SizedBox(width: 10),
        Expanded(
          child: Text(label,
              style: const TextStyle(fontSize: 12.5, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
        ),
        Flexible(
          child: Text(value, textAlign: TextAlign.right,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }

  Widget _statusPill(String status) {
    final (color, label) = switch (status) {
      'active' => (BuzUpColors.success, 'ACTIVO'),
      'exhausted' => (BuzUpColors.danger, 'ESGOTADO'),
      'expired' => (BuzUpColors.danger, 'EXPIRADO'),
      'cancelled' => (BuzUpColors.danger, 'CANCELADO'),
      _ => (Colors.white70, status.toUpperCase()),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(label,
          style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 0.6)),
    );
  }

  String _discountTypeLabel(String t, String v) => switch (t) {
        'fixed_amount' => 'PACOTE DE SALDO ESPECIAL',
        'free_trips' => 'PACOTE DE VIAGENS GRATIS',
        'percentage' => 'DESCONTO PERCENTUAL $v%',
        _ => t.toUpperCase(),
      };

  String _daysLeftLabel(String? iso) {
    if (iso == null) return '-';
    try {
      final exp = DateTime.parse(iso).toLocal();
      final days = exp.difference(DateTime.now()).inDays;
      if (days < 0) return 'Expirado';
      if (days == 0) return 'Expira hoje';
      return '$days dia${days == 1 ? '' : 's'}';
    } catch (_) {
      return iso;
    }
  }

  String _fmt(String iso) {
    if (iso.isEmpty) return '-';
    try {
      return DateFormat('dd/MM/yyyy HH:mm', 'pt_PT').format(DateTime.parse(iso).toLocal());
    } catch (_) {
      return iso;
    }
  }

  String _money(num v) => NumberFormat('#,##0.00', 'pt_PT').format(v);
}
