import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class PackagesScreen extends ConsumerStatefulWidget {
  const PackagesScreen({super.key});

  @override
  ConsumerState<PackagesScreen> createState() => _PackagesScreenState();
}

class _PackagesScreenState extends ConsumerState<PackagesScreen> {
  int? _buying;
  String? _error;
  String? _success;

  /// Confirms with the passenger before charging the wallet — no silent,
  /// one-tap purchase. Shows price, validity, trips and the resulting balance.
  Future<void> _confirmSubscribe(Map p, double balance) async {
    final id = (p['id'] as int?) ?? 0;
    if (id == 0) return;
    final price = double.tryParse('${p['price'] ?? 0}') ?? 0;
    final name = p['name']?.toString() ?? '-';
    final after = balance - price;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirmar compra'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 10),
            _confirmRow('Validade', '${p['validity_days'] ?? 0} dias'),
            _confirmRow('Viagens', '${p['max_trips'] ?? 0} viagens'),
            const Divider(height: 18),
            _confirmRow('Preco', '${price.toStringAsFixed(2)} MZN', bold: true),
            _confirmRow('Saldo apos compra', '${after.toStringAsFixed(2)} MZN'),
            const SizedBox(height: 10),
            const Text('O valor sera debitado da sua carteira BuzUp.',
                style: TextStyle(fontSize: 12, color: BuzUpColors.muted)),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Pagar'),
          ),
        ],
      ),
    );
    if (ok == true) await _subscribe(id);
  }

  Widget _confirmRow(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(children: [
        Expanded(
          child: Text(label,
              style: TextStyle(
                  fontSize: 13,
                  color: BuzUpColors.muted,
                  fontWeight: bold ? FontWeight.w800 : FontWeight.w600)),
        ),
        Text(value,
            style: TextStyle(fontSize: 13.5, fontWeight: bold ? FontWeight.w900 : FontWeight.w700)),
      ]),
    );
  }

  Future<void> _subscribe(int id) async {
    setState(() {
      _buying = id;
      _error = null;
      _success = null;
    });
    try {
      await ref.read(passengerApiProvider).subscribePackage(id);
      setState(() => _success = 'Pacote activado.');
      ref.invalidate(meProvider);
    } on DioException catch (e) {
      setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _buying = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final me = ref.watch(meProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pacotes', style: TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async => ref.invalidate(meProvider),
          child: me.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => ListView(children: [
              Padding(
                padding: const EdgeInsets.all(20),
                child: Text('Erro: $e', style: const TextStyle(color: BuzUpColors.danger)),
              ),
            ]),
            data: (data) => _content(data),
          ),
        ),
      ),
    );
  }

  Widget _content(Map<String, dynamic> data) {
    final active = (data['active_packages'] as List?) ?? const [];
    final available = (data['available_packages'] as List?) ?? const [];
    final balance = double.tryParse('${data['balance'] ?? 0}') ?? 0;

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      children: [
        // Banner with current balance reminder
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: BuzUpColors.orange.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: BuzUpColors.orange.withValues(alpha: 0.30)),
          ),
          child: Row(children: [
            const Icon(Icons.account_balance_wallet, color: BuzUpColors.orange, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(
              'Saldo disponivel: ${balance.toStringAsFixed(2)} MZN',
              style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700),
            )),
          ]),
        ),
        const SizedBox(height: 14),
        if (_success != null)
          _banner(_success!, BuzUpColors.success, Icons.check_circle),
        if (_error != null)
          _banner(_error!, BuzUpColors.danger, Icons.error_outline),
        if (active.isNotEmpty) ...[
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 6),
            child: Text('PACOTES ACTIVOS',
                style: TextStyle(fontSize: 11, letterSpacing: 1.4,
                    color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
          ),
          for (final p in active.cast<Map>()) _activeTile(p),
          const SizedBox(height: 14),
        ],
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 6),
          child: Text('DISPONIVEIS',
              style: TextStyle(fontSize: 11, letterSpacing: 1.4,
                  color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
        ),
        if (available.isEmpty)
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: BuzUpColors.border),
            ),
            child: const Center(child: Text('Nao existem pacotes disponiveis no momento.',
                style: TextStyle(color: BuzUpColors.muted))),
          )
        else
          for (final p in available.cast<Map>()) _availableTile(p, balance),
      ],
    );
  }

  Widget _activeTile(Map p) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1FB04A), Color(0xFF2DC76A)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(color: BuzUpColors.success.withValues(alpha: 0.25),
              blurRadius: 14, offset: const Offset(0, 6)),
        ],
      ),
      child: Row(children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.20),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.card_giftcard, color: Colors.white),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(p['package_name']?.toString() ?? '-',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14)),
            const SizedBox(height: 2),
            Text('${p['trips_remaining'] ?? 0} viagens restantes',
                style: const TextStyle(color: Colors.white70, fontSize: 11.5)),
            Text('Expira: ${(p['expires_at'] ?? '').toString().split('T').first}',
                style: const TextStyle(color: Colors.white70, fontSize: 11)),
          ]),
        ),
        const Icon(Icons.check_circle, color: Colors.white, size: 26),
      ]),
    );
  }

  Widget _availableTile(Map p, double balance) {
    final price = double.tryParse('${p['price'] ?? 0}') ?? 0;
    final id = (p['id'] as int?) ?? 0;
    final isAffordable = balance >= price;
    final isBusy = _buying == id;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: BuzUpColors.border),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
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
              Text(p['name']?.toString() ?? '-',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
              const SizedBox(height: 2),
              Wrap(spacing: 6, runSpacing: 4, children: [
                _chip(Icons.calendar_today, '${p['validity_days'] ?? 0} dias'),
                _chip(Icons.directions_bus, '${p['max_trips'] ?? 0} viagens'),
              ]),
            ]),
          ),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('${price.toStringAsFixed(0)}',
                style: const TextStyle(color: BuzUpColors.orange, fontSize: 20, fontWeight: FontWeight.w800)),
            const Text('MZN',
                style: TextStyle(color: BuzUpColors.muted, fontSize: 10, letterSpacing: 0.8, fontWeight: FontWeight.w700)),
          ]),
        ]),
        if ((p['description'] as String?)?.isNotEmpty == true) ...[
          const SizedBox(height: 8),
          Text(p['description'].toString(),
              style: const TextStyle(fontSize: 12, color: BuzUpColors.muted, height: 1.4)),
        ],
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          height: 44,
          child: FilledButton(
            onPressed: (!isAffordable || isBusy || id == 0) ? null : () => _confirmSubscribe(p, balance),
            style: FilledButton.styleFrom(
              backgroundColor: isAffordable ? BuzUpColors.orange : Colors.grey,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              textStyle: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800),
            ),
            child: isBusy
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : Text(isAffordable
                    ? 'COMPRAR COM A CARTEIRA'
                    : 'SALDO INSUFICIENTE'),
          ),
        ),
      ]),
    );
  }

  Widget _chip(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: BuzUpColors.muted.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 11, color: BuzUpColors.muted),
        const SizedBox(width: 4),
        Text(text, style: const TextStyle(fontSize: 10.5, color: BuzUpColors.muted, fontWeight: FontWeight.w700)),
      ]),
    );
  }

  Widget _banner(String text, Color color, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.30)),
      ),
      child: Row(children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 8),
        Expanded(child: Text(text, style: TextStyle(color: color, fontSize: 12.5, fontWeight: FontWeight.w700))),
      ]),
    );
  }
}
