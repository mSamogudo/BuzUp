import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/feedback.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// Viagens do motorista: lista agrupada + ciclo iniciar/pausar/retomar/terminar.
/// So acessivel a utilizadores com perfil de motorista activo (a home esconde
/// a entrada para os restantes; o backend valida sempre a alocacao da viagem).
class DriverTripsScreen extends ConsumerStatefulWidget {
  const DriverTripsScreen({super.key});

  @override
  ConsumerState<DriverTripsScreen> createState() => _DriverTripsScreenState();
}

class _DriverTripsScreenState extends ConsumerState<DriverTripsScreen> {
  Timer? _refreshTimer;
  int? _busyTripId;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(const Duration(seconds: 45), (_) {
      ref.invalidate(driverTripsProvider);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _run(int tripId, String action) async {
    setState(() => _busyTripId = tripId);
    try {
      // No arranque, o terminal identifica-se: passa a ser a fonte da posicao
      // do autocarro no mapa dos passageiros.
      final serial = action == 'start'
          ? await ref.read(secureStoreProvider).getDeviceSerial()
          : null;
      final res = await ref.read(agentApiProvider).driverTripAction(tripId, action, deviceSerial: serial);
      await AppFeedback.success();
      ref.invalidate(driverTripsProvider);
      if (action == 'close' && mounted) _showCloseSummary(res);
    } on DioException catch (e) {
      await AppFeedback.error();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ApiClient.extractError(e)), backgroundColor: BuzUpColors.danger),
        );
      }
    } finally {
      if (mounted) setState(() => _busyTripId = null);
    }
  }

  Future<void> _confirmClose(Map<String, dynamic> trip) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Terminar viagem?'),
        content: Text('${trip['route_code'] ?? ''} · ${trip['route_name'] ?? ''}\n'
            'A viagem sera fechada e o resumo apurado.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('TERMINAR')),
        ],
      ),
    );
    if (ok == true) await _run(trip['id'] as int, 'close');
  }

  void _showCloseSummary(Map<String, dynamic> trip) {
    final closure = (trip['closure_summary'] as Map?)?.cast<String, dynamic>() ?? const {};
    final validations = (closure['validations'] as Map?)?.cast<String, dynamic>() ?? const {};
    final approved = validations['approved'] ?? 0;
    final denied = validations['denied'] ?? 0;
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Viagem terminada'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${trip['route_code'] ?? ''} · ${trip['route_name'] ?? ''}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            Text('Validacoes: $approved aprovadas, $denied negadas'),
            const SizedBox(height: 6),
            Text('Receita da viagem: ${closure['total_revenue'] ?? '0.00'} MZN',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
        ),
        actions: [
          FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tripsAsync = ref.watch(driverTripsProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardBg = isDark ? const Color(0xFF152444) : Colors.white;
    final txtMain = isDark ? Colors.white : BuzUpColors.navy;
    final txtMuted = txtMain.withValues(alpha: 0.6);
    final borderColor = isDark ? Colors.white12 : const Color(0xFFE5E0D5);

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F1A35) : const Color(0xFFF7F4EE),
      appBar: AppBar(title: const Text('Minhas viagens')),
      body: tripsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _errorState(e, txtMuted),
        data: (trips) {
          if (trips.isEmpty) return _emptyState(txtMain, txtMuted);
          final groups = _group(trips);
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(driverTripsProvider),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                for (final g in groups.entries) ...[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(2, 14, 2, 8),
                    child: Text(g.key.toUpperCase(),
                        style: TextStyle(color: txtMuted, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.1)),
                  ),
                  for (final t in g.value) _tripCard(t, cardBg, txtMain, txtMuted, borderColor),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _errorState(Object e, Color txtMuted) {
    final msg = e is DioException ? ApiClient.extractError(e) : e.toString();
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.cloud_off, color: txtMuted, size: 40),
          const SizedBox(height: 10),
          Text(msg, textAlign: TextAlign.center, style: TextStyle(color: txtMuted)),
          const SizedBox(height: 14),
          OutlinedButton(
            onPressed: () => ref.invalidate(driverTripsProvider),
            child: const Text('Tentar de novo'),
          ),
        ]),
      ),
    );
  }

  Widget _emptyState(Color txtMain, Color txtMuted) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.departure_board, color: txtMuted, size: 44),
          const SizedBox(height: 12),
          Text('Sem viagens alocadas',
              style: TextStyle(color: txtMain, fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Text('Quando o gestor alocar viagens a si,\naparecem aqui.',
              textAlign: TextAlign.center, style: TextStyle(color: txtMuted, fontSize: 13)),
        ]),
      ),
    );
  }

  Map<String, List<Map<String, dynamic>>> _group(List<Map<String, dynamic>> trips) {
    final now = DateTime.now();
    final active = <Map<String, dynamic>>[];
    final today = <Map<String, dynamic>>[];
    final upcoming = <Map<String, dynamic>>[];
    for (final t in trips) {
      if (kActiveTripStatuses.contains(t['status'])) {
        active.add(t);
        continue;
      }
      final dep = DateTime.tryParse((t['planned_departure_at'] ?? '').toString())?.toLocal();
      if (dep != null && dep.year == now.year && dep.month == now.month && dep.day == now.day) {
        today.add(t);
      } else {
        upcoming.add(t);
      }
    }
    return {
      if (active.isNotEmpty) 'Em curso': active,
      if (today.isNotEmpty) 'Hoje': today,
      if (upcoming.isNotEmpty) 'Proximas': upcoming,
    };
  }

  Widget _tripCard(Map<String, dynamic> t, Color cardBg, Color txtMain, Color txtMuted, Color border) {
    final id = t['id'] as int;
    final status = (t['status'] ?? '').toString();
    final busy = _busyTripId == id;
    final vehicle = (t['vehicle_registration'] ?? '').toString();
    final hasVehicle = vehicle.isNotEmpty;
    final dep = DateTime.tryParse((t['planned_departure_at'] ?? '').toString())?.toLocal();
    final depLabel = dep == null
        ? '—'
        : '${dep.day.toString().padLeft(2, '0')}/${dep.month.toString().padLeft(2, '0')} '
          '${dep.hour.toString().padLeft(2, '0')}:${dep.minute.toString().padLeft(2, '0')}';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: kActiveTripStatuses.contains(status) ? BuzUpColors.blueDark.withValues(alpha: 0.55) : border,
        ),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: Text('${t['route_code'] ?? ''} · ${t['route_name'] ?? ''}',
                style: TextStyle(color: txtMain, fontSize: 15, fontWeight: FontWeight.w700),
                overflow: TextOverflow.ellipsis),
          ),
          _statusChip(status),
        ]),
        const SizedBox(height: 6),
        Text(
          hasVehicle ? 'Partida $depLabel · Viatura $vehicle' : 'Partida $depLabel',
          style: TextStyle(color: txtMuted, fontSize: 12),
        ),
        if (!hasVehicle && status == 'scheduled')
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('Viagem incompleta: falta a viatura. Fale com o gestor.',
                style: TextStyle(color: BuzUpColors.danger.withValues(alpha: 0.9), fontSize: 12)),
          ),
        const SizedBox(height: 12),
        if (busy)
          const Center(child: Padding(
            padding: EdgeInsets.symmetric(vertical: 6),
            child: SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2.4)),
          ))
        else
          Row(children: _actionsFor(id, status, hasVehicle, t)),
      ]),
    );
  }

  List<Widget> _actionsFor(int id, String status, bool hasVehicle, Map<String, dynamic> t) {
    Widget primary(String label, VoidCallback? onTap) => Expanded(
          child: FilledButton(
            onPressed: onTap,
            style: FilledButton.styleFrom(
              backgroundColor: BuzUpColors.blue,
              padding: const EdgeInsets.symmetric(vertical: 12),
            ),
            child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.8)),
          ),
        );
    Widget secondary(String label, VoidCallback onTap) => Expanded(
          child: OutlinedButton(
            onPressed: onTap,
            style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 12)),
            child: Text(label),
          ),
        );

    switch (status) {
      case 'scheduled':
        return [primary('INICIAR', hasVehicle ? () => _run(id, 'start') : null)];
      case 'boarding':
      case 'departed':
        return [
          secondary('Pausar', () => _run(id, 'pause')),
          const SizedBox(width: 10),
          primary('TERMINAR', () => _confirmClose(t)),
        ];
      case 'paused':
        return [
          secondary('Retomar', () => _run(id, 'resume')),
          const SizedBox(width: 10),
          primary('TERMINAR', () => _confirmClose(t)),
        ];
      default:
        return const [SizedBox.shrink()];
    }
  }

  Widget _statusChip(String status) {
    final (label, color) = switch (status) {
      'boarding' => ('EMBARQUE', BuzUpColors.blueDark),
      'departed' => ('EM VIAGEM', BuzUpColors.success),
      'paused' => ('PAUSADA', Color(0xFFB58900)),
      'scheduled' => ('AGENDADA', BuzUpColors.blue),
      _ => (status.toUpperCase(), BuzUpColors.navy),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.6)),
    );
  }
}
