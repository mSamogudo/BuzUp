import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/bus_loader.dart';
import '../../core/logger.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class BuyTicketScreen extends ConsumerStatefulWidget {
  const BuyTicketScreen({super.key});

  @override
  ConsumerState<BuyTicketScreen> createState() => _BuyTicketScreenState();
}

class _BuyTicketScreenState extends ConsumerState<BuyTicketScreen> {
  Future<Map<String, dynamic>>? _trips;
  Map<String, dynamic>? _quote;
  bool _quoting = false;
  bool _purchasing = false;
  String? _error;

  int? _originId;
  int? _destinationId;
  bool _usePackage = true;

  @override
  void initState() {
    super.initState();
    _trips = ref.read(passengerApiProvider).publicTrips();
  }

  Future<void> _refreshQuote() async {
    if (_originId == null || _destinationId == null) {
      setState(() => _quote = null);
      return;
    }
    setState(() {
      _quoting = true;
      _error = null;
    });
    try {
      final res = await ref.read(passengerApiProvider).quoteTicket(
            originStopId: _originId,
            destinationStopId: _destinationId,
            usePackage: _usePackage,
          );
      Log.info('ticket.quote ok', data: res);
      if (!mounted) return;
      setState(() => _quote = res);
    } on DioException catch (e) {
      Log.warn('ticket.quote failed', error: e.message);
      if (!mounted) return;
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _quoting = false);
    }
  }

  Future<void> _purchase() async {
    if (_originId == null || _destinationId == null) return;
    setState(() {
      _purchasing = true;
      _error = null;
    });
    try {
      final res = await ref.read(passengerApiProvider).purchaseTicket(
            originStopId: _originId,
            destinationStopId: _destinationId,
            usePackage: _usePackage,
          );
      Log.info('ticket.purchase ok', data: 'id=${res['id']}');
      ref.invalidate(meProvider);
      if (!mounted) return;
      final id = res['id'];
      if (id is int) {
        context.go('/tickets/$id');
      } else {
        context.go('/tickets');
      }
    } on DioException catch (e) {
      Log.warn('ticket.purchase failed', error: e.message);
      if (!mounted) return;
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _purchasing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Comprar bilhete'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.canPop() ? context.pop() : context.go('/tickets'),
        ),
      ),
      body: SafeArea(
        child: FutureBuilder<Map<String, dynamic>>(
          future: _trips,
          builder: (ctx, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: BusLoader(label: 'A carregar paragens...'));
            }
            if (snap.hasError) {
              return Center(child: Text('Erro: ${snap.error}', style: const TextStyle(color: BuzUpColors.danger)));
            }
            final data = snap.data ?? const {};
            final stops = (data['stops'] as List?)?.cast<Map>() ?? const [];
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                _dropdown<int>(
                  label: 'Origem',
                  value: _originId,
                  items: [for (final s in stops)
                    if (s['id'] != _destinationId)
                      DropdownMenuItem(value: s['id'] as int, child: Text(s['name']?.toString() ?? '-'))],
                  onChanged: (v) {
                    setState(() => _originId = v);
                    _refreshQuote();
                  },
                ),
                const SizedBox(height: 12),
                _dropdown<int>(
                  label: 'Destino',
                  value: _destinationId,
                  items: [for (final s in stops)
                    if (s['id'] != _originId)
                      DropdownMenuItem(value: s['id'] as int, child: Text(s['name']?.toString() ?? '-'))],
                  onChanged: (v) {
                    setState(() => _destinationId = v);
                    _refreshQuote();
                  },
                ),
                const SizedBox(height: 12),
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  value: _usePackage,
                  onChanged: (v) {
                    setState(() => _usePackage = v);
                    _refreshQuote();
                  },
                  title: const Text('Usar pacote especial se disponivel'),
                  subtitle: const Text('Quando activo, desconta primeiro do saldo do pacote.', style: TextStyle(fontSize: 11.5, color: BuzUpColors.muted)),
                ),
                const SizedBox(height: 8),
                _quoteCard(),
                if (_error != null) Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(_error!, style: const TextStyle(color: BuzUpColors.danger, fontSize: 12.5)),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: (_originId == null || _destinationId == null || _purchasing) ? null : _purchase,
                  child: _purchasing
                      ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : Text(_payButtonLabel()),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _dropdown<T>({
    required String label,
    required T? value,
    required List<DropdownMenuItem<T>> items,
    required ValueChanged<T?> onChanged,
  }) {
    return InputDecorator(
      decoration: InputDecoration(labelText: label),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<T>(
          isExpanded: true,
          value: value,
          items: items,
          onChanged: onChanged,
          hint: const Text('Seleccione...', style: TextStyle(color: BuzUpColors.muted)),
        ),
      ),
    );
  }

  Widget _quoteCard() {
    if (_quoting) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Theme.of(context).colorScheme.outline),
        ),
        child: const Center(child: BusLoader(size: 110, label: 'A calcular...')),
      );
    }
    if (_quote == null) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Theme.of(context).colorScheme.outline),
        ),
        child: const Text(
          'Seleccione origem e destino para ver o preco.',
          style: TextStyle(fontSize: 12.5, color: BuzUpColors.muted),
        ),
      );
    }
    // Quote response keys (from backend): base_fare, wallet_amount,
    // package_id, package_name, discount_type.
    final base = double.tryParse('${_quote!['base_fare'] ?? _quote!['fare_amount'] ?? 0}') ?? 0;
    final walletAmount = double.tryParse('${_quote!['wallet_amount'] ?? base}') ?? base;
    final packageName = (_quote!['package_name'] ?? '').toString();
    final discountType = (_quote!['discount_type'] ?? '').toString();
    final hasPackage = (_quote!['package_id'] ?? null) != null && packageName.isNotEmpty;
    final discount = (base - walletAmount).clamp(0, base);
    final fullyCoveredByPackage = walletAmount <= 0 && hasPackage;
    final fmt = (num n) =>
        '${n.toStringAsFixed(2).replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+\.)'), (m) => '${m[1]} ')} MZN';

    Widget row(String label, String value, {Color? color, FontWeight? bold, IconData? icon}) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [
          if (icon != null) Padding(
            padding: const EdgeInsets.only(right: 6),
            child: Icon(icon, size: 14, color: color ?? Colors.white70),
          ),
          Expanded(child: Text(label,
              style: TextStyle(color: color ?? Colors.white70, fontSize: 12.5, fontWeight: bold ?? FontWeight.w600))),
          Text(value,
              style: TextStyle(color: color ?? Colors.white, fontSize: 12.5, fontWeight: bold ?? FontWeight.w800)),
        ]),
      );
    }

    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [BuzUpColors.navy, BuzUpColors.navyDark],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('RESUMO DA COMPRA',
            style: TextStyle(color: Colors.white70, fontSize: 10.5, letterSpacing: 1.6, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        row('Tarifa base', fmt(base), icon: Icons.directions_bus),
        if (hasPackage) ...[
          const Divider(color: Colors.white24, height: 14),
          row('Pacote', packageName,
              color: BuzUpColors.orangeDark, bold: FontWeight.w900, icon: Icons.card_giftcard),
          if (discount > 0)
            row(_discountLabel(discountType), '-${fmt(discount.toDouble())}',
                color: const Color(0xFF6FE38B), icon: Icons.local_offer),
        ],
        const Divider(color: Colors.white24, height: 16),
        Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
          const Expanded(
            child: Text('A PAGAR DA CARTEIRA',
                style: TextStyle(color: Colors.white, fontSize: 11.5, letterSpacing: 1.2, fontWeight: FontWeight.w900)),
          ),
          Text(fmt(walletAmount),
              style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900, letterSpacing: -0.3)),
        ]),
        if (fullyCoveredByPackage) Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(children: const [
            Icon(Icons.check_circle, color: Color(0xFF6FE38B), size: 16),
            SizedBox(width: 6),
            Expanded(child: Text(
              'Totalmente coberto pelo pacote — nada sai da carteira.',
              style: TextStyle(color: Color(0xFFB9F3CB), fontSize: 11.5, fontWeight: FontWeight.w700),
            )),
          ]),
        ),
      ]),
    );
  }

  String _discountLabel(String discountType) => switch (discountType) {
        'percentage' => 'Desconto pacote (%)',
        'free_trips' => 'Viagens gratis do pacote',
        'fixed_amount' => 'Saldo especial do pacote',
        _ => 'Desconto do pacote',
      };

  String _payButtonLabel() {
    if (_quote == null) return 'COMPRAR BILHETE';
    final walletAmount = double.tryParse('${_quote!['wallet_amount'] ?? 0}') ?? 0;
    if (walletAmount <= 0) return 'USAR PACOTE - GRATIS';
    final fmt = walletAmount.toStringAsFixed(2)
        .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+\.)'), (m) => '${m[1]} ');
    return 'PAGAR $fmt MZN';
  }
}
