import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/bus_loader.dart';
import '../../core/logger.dart';
import '../../core/providers.dart';
import '../../core/seat_picker.dart';
import '../../core/theme.dart';
import 'stop_picker.dart';

/// Como o passageiro paga o bilhete: com o saldo BusUp (fluxo original) ou
/// directamente com M-Pesa/e-Mola, sem ser obrigado a carregar a carteira.
enum _PayMethod { wallet, mobileMoney }

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
  String? _waitingMessage;

  int? _originId;
  int? _destinationId;

  // Lugar marcado. A app nunca pergunta ao passageiro que tipo de viagem e:
  // o orcamento devolve `requires_seat_selection` a partir da rota que liga a
  // origem ao destino, e so entao aparecem a partida e a planta. Numa carreira
  // urbana estes passos nem existem.
  bool _seatsRequired = false;
  DateTime _travelDate = DateTime.now();
  List<Map<String, dynamic>> _departures = const [];
  bool _loadingDepartures = false;
  int? _tripId;
  Map<String, dynamic>? _seatMap;
  String? _seat;
  List<Map> _stops = const [];
  bool _usePackage = true;

  _PayMethod _method = _PayMethod.wallet;
  final _phoneCtrl = TextEditingController();

  // Moeda de exibicao (rand nas rotas p/ Africa do Sul). So visual: a
  // cobranca e sempre em meticais; a escolha fica gravada no bilhete.
  Map<String, double> _rates = const {};
  String _currency = 'MZN';

  @override
  void initState() {
    super.initState();
    _trips = ref.read(passengerApiProvider).publicTrips();
    ref.read(passengerApiProvider).exchangeRates().then((d) {
      final parsed = <String, double>{};
      (d['rates'] as Map?)?.forEach((k, v) {
        final n = double.tryParse('$v');
        if (n != null && n > 0) parsed['$k'] = n;
      });
      if (mounted) setState(() => _rates = parsed);
    }).catchError((_) {});
    // Prefill do telemovel com o numero da conta (o passageiro pode trocar).
    ref.read(passengerApiProvider).me().then((me) {
      final phone = (me['phone'] ?? '').toString();
      if (mounted && _phoneCtrl.text.isEmpty && phone.isNotEmpty) {
        _phoneCtrl.text = phone.startsWith('258') ? phone.substring(3) : phone;
      }
    }).catchError((_) {});
  }

  @override
  void dispose() {
    _phoneCtrl.dispose();
    super.dispose();
  }

  double? get _rate => _currency == 'MZN' ? null : _rates[_currency];

  String _fmtMzn(num n) =>
      '${n.toStringAsFixed(2).replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+\.)'), (m) => '${m[1]} ')} MZN';

  String _fmtDisplay(num mzn) {
    final r = _rate;
    if (r == null) return _fmtMzn(mzn);
    return '${(mzn / r).toStringAsFixed(2)} $_currency';
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
      final needsSeat = res['requires_seat_selection'] == true;
      setState(() {
        _quote = res;
        if (needsSeat != _seatsRequired) {
          // Mudar de uma carreira urbana para uma interprovincial (ou o
          // contrario) invalida a partida e o lugar escolhidos antes.
          _seatsRequired = needsSeat;
          _tripId = null;
          _seat = null;
          _seatMap = null;
          _departures = const [];
        }
      });
      if (_seatsRequired) await _loadDepartures();
    } on DioException catch (e) {
      Log.warn('ticket.quote failed', error: e.message);
      if (!mounted) return;
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _quoting = false);
    }
  }

  String get _dateIso =>
      '${_travelDate.year.toString().padLeft(4, "0")}-'
      '${_travelDate.month.toString().padLeft(2, "0")}-'
      '${_travelDate.day.toString().padLeft(2, "0")}';

  Future<void> _loadDepartures() async {
    if (_originId == null || _destinationId == null) return;
    setState(() {
      _loadingDepartures = true;
      _departures = const [];
      _tripId = null;
      _seat = null;
      _seatMap = null;
    });
    try {
      final items = await ref.read(passengerApiProvider).searchDepartures(
            originStopId: _originId!,
            destinationStopId: _destinationId!,
            date: _dateIso,
          );
      if (!mounted) return;
      // So partidas ainda a venda: mostrar as esgotadas dava um toque sem
      // resposta e a impressao de que a compra falhou.
      setState(() => _departures = items.where((t) => t['on_sale'] == true).toList());
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _loadingDepartures = false);
    }
  }

  Future<void> _selectDeparture(int tripId) async {
    setState(() {
      _tripId = tripId;
      _seat = null;
      _seatMap = null;
    });
    try {
      final map = await ref.read(passengerApiProvider).tripSeats(tripId);
      if (!mounted) return;
      setState(() => _seatMap = map);
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _error = ApiClient.extractError(e));
    }
  }

  Future<void> _purchaseWithWallet() async {
    try {
      final res = await ref.read(passengerApiProvider).purchaseTicket(
            originStopId: _originId,
            destinationStopId: _destinationId,
            tripId: _tripId,
            seat: _seat,
            usePackage: _usePackage,
            displayCurrency: _currency,
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
    }
  }

  /// Compra directa: cria o checkout (dispara o pedido de PIN) e faz polling
  /// ate o pagamento confirmar e o bilhete ser emitido na conta.
  Future<void> _purchaseWithMobileMoney() async {
    final phone = _phoneCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (phone.length < 9) {
      setState(() => _error = 'Indique o numero de telemovel que paga (9 digitos).');
      return;
    }
    Map? originStop;
    Map? destStop;
    for (final s in _stops) {
      if (s['id'] == _originId) originStop = s;
      if (s['id'] == _destinationId) destStop = s;
    }
    try {
      setState(() => _waitingMessage = 'A contactar a carteira movel...');
      final res = await ref.read(passengerApiProvider).directCheckout(
            originStopId: _originId!,
            destinationStopId: _destinationId!,
            originName: (originStop?['name'] ?? '').toString(),
            destinationName: (destStop?['name'] ?? '').toString(),
            payerPhone: phone,
            tripId: _tripId,
            seat: _seat,
            displayCurrency: _currency,
          );
      Log.info('ticket.direct ok', data: 'ref=${res['checkout_reference']} status=${res['status']}');
      final reference = (res['checkout_reference'] ?? '').toString();
      if (reference.isEmpty) {
        throw StateError('Resposta sem referencia de checkout.');
      }
      if (res['status'] == 'issued') {
        await _finishDirectPurchase(reference);
        return;
      }
      if (mounted) {
        setState(() => _waitingMessage =
            'Confirme o pagamento no telemovel $phone quando o PIN for pedido.');
      }
      await _pollCheckout(reference);
    } on DioException catch (e) {
      Log.warn('ticket.direct failed', error: e.message);
      if (!mounted) return;
      setState(() {
        _error = ApiClient.extractError(e);
        _waitingMessage = null;
      });
    }
  }

  Future<void> _pollCheckout(String reference) async {
    // ~2 minutos: o pedido de PIN do M-Pesa/e-Mola expira antes disso.
    for (var i = 0; i < 40; i++) {
      await Future<void>.delayed(const Duration(seconds: 3));
      if (!mounted) return;
      Map<String, dynamic> st;
      try {
        st = await ref.read(passengerApiProvider).checkoutStatus(reference);
      } on DioException {
        continue; // rede instavel: tentar de novo no proximo tick
      }
      final s = (st['status'] ?? '').toString();
      if (s == 'issued') {
        await _finishDirectPurchase(reference, statusPayload: st);
        return;
      }
      if (s == 'cancelled' || s == 'expired') {
        if (!mounted) return;
        setState(() {
          _error = 'O pagamento nao foi concluido. Nenhum valor foi debitado alem do pedido cancelado.';
          _waitingMessage = null;
        });
        return;
      }
    }
    if (!mounted) return;
    setState(() {
      _error = 'Tempo esgotado a aguardar a confirmacao. Verifique nos seus bilhetes '
          'antes de tentar de novo — o pagamento pode ainda ser confirmado.';
      _waitingMessage = null;
    });
  }

  Future<void> _finishDirectPurchase(String reference, {Map<String, dynamic>? statusPayload}) async {
    var payload = statusPayload;
    if (payload == null) {
      try {
        payload = await ref.read(passengerApiProvider).checkoutStatus(reference);
      } on DioException {
        payload = const {};
      }
    }
    ref.invalidate(meProvider);
    if (!mounted) return;
    final passes = (payload['passes'] as List?)?.cast<Map>() ?? const [];
    final id = passes.isNotEmpty ? passes.first['id'] : null;
    if (id is int) {
      context.go('/tickets/$id');
    } else {
      context.go('/tickets');
    }
  }

  Future<void> _purchase() async {
    if (_originId == null || _destinationId == null) return;
    setState(() {
      _purchasing = true;
      _error = null;
    });
    try {
      if (_method == _PayMethod.wallet) {
        await _purchaseWithWallet();
      } else {
        await _purchaseWithMobileMoney();
      }
    } finally {
      if (mounted) {
        setState(() {
          _purchasing = false;
          _waitingMessage = null;
        });
      }
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
            _stops = (data['stops'] as List?)?.cast<Map>() ?? const [];
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                StopPickerField(
                  label: 'Origem',
                  stops: _stops,
                  selectedId: _originId,
                  excludeId: _destinationId,
                  onChanged: (v) {
                    setState(() => _originId = v);
                    _refreshQuote();
                  },
                ),
                const SizedBox(height: 12),
                StopPickerField(
                  label: 'Destino',
                  stops: _stops,
                  selectedId: _destinationId,
                  excludeId: _originId,
                  onChanged: (v) {
                    setState(() => _destinationId = v);
                    _refreshQuote();
                  },
                ),
                if (_seatsRequired) ...[
                  const SizedBox(height: 12),
                  _departurePicker(),
                  if (_seatMap != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _seat == null ? 'Escolha o seu lugar' : 'Lugar $_seat',
                      style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 8),
                    SeatPicker(
                      seatMap: _seatMap!,
                      picked: _seat == null ? const [] : [_seat!],
                      maxPick: 1,
                      onToggle: (label) => setState(() => _seat = _seat == label ? null : label),
                    ),
                  ],
                ],
                const SizedBox(height: 12),
                _methodSelector(),
                if (_method == _PayMethod.wallet)
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
                if (_method == _PayMethod.mobileMoney) ...[
                  const SizedBox(height: 4),
                  TextField(
                    controller: _phoneCtrl,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(
                      labelText: 'Telemovel que paga (M-Pesa ou e-Mola)',
                      hintText: '84xxxxxxx / 86xxxxxxx',
                      helperText: 'Vai receber o pedido de PIN neste numero.',
                    ),
                  ),
                ],
                const SizedBox(height: 8),
                if (_rates.isNotEmpty) _currencySelector(),
                const SizedBox(height: 8),
                _quoteCard(),
                if (_waitingMessage != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: Row(children: [
                      const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                      const SizedBox(width: 10),
                      Expanded(child: Text(_waitingMessage!, style: const TextStyle(fontSize: 12.5))),
                    ]),
                  ),
                if (_error != null) Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(_error!, style: const TextStyle(color: BuzUpColors.danger, fontSize: 12.5)),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: (_originId == null ||
                          _destinationId == null ||
                          _purchasing ||
                          // Nas interprovinciais nao se compra sem partida nem
                          // lugar — o servidor recusa, e mais vale o botao
                          // dizer porque do que a compra falhar depois.
                          (_seatsRequired && (_tripId == null || _seat == null)))
                      ? null
                      : _purchase,
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

  /// Data e lista de partidas do dia. So aparece nas rotas com lugar marcado,
  /// onde o bilhete se compra para uma partida concreta e nao para "o proximo
  /// autocarro que vier".
  Widget _departurePicker() {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: scheme.outline),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          const Expanded(
            child: Text('Partida', style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
          ),
          TextButton.icon(
            icon: const Icon(Icons.calendar_today, size: 15),
            label: Text(_dateIso),
            onPressed: () async {
              final now = DateTime.now();
              final picked = await showDatePicker(
                context: context,
                initialDate: _travelDate,
                firstDate: DateTime(now.year, now.month, now.day),
                lastDate: now.add(const Duration(days: 90)),
              );
              if (picked == null) return;
              setState(() => _travelDate = picked);
              await _loadDepartures();
            },
          ),
        ]),
        if (_loadingDepartures)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 14),
            child: Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))),
          )
        else if (_departures.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Text(
              'Sem partidas a venda nesta data. Escolha outro dia.',
              style: TextStyle(fontSize: 12.5, color: BuzUpColors.muted),
            ),
          )
        else
          for (final t in _departures) _departureTile(t),
      ]),
    );
  }

  Widget _departureTile(Map<String, dynamic> t) {
    final id = t['trip_id'] as int?;
    final selected = id != null && id == _tripId;
    final departure = (t['departure'] ?? '').toString();
    final hour = departure.length >= 16 ? departure.substring(11, 16) : '--:--';
    final seats = t['seats_available'];
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: id == null ? null : () => _selectDeparture(id),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(10),
            color: selected ? BuzUpColors.blue.withValues(alpha: 0.08) : null,
            border: Border.all(
              color: selected ? BuzUpColors.blue : const Color(0xFFE4EBF3),
              width: selected ? 1.6 : 1,
            ),
          ),
          child: Row(children: [
            Icon(selected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                size: 18, color: selected ? BuzUpColors.blue : BuzUpColors.muted),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(hour, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
                Text(
                  '${t['route_name'] ?? t['route_code'] ?? ''}'
                  '${t['vehicle'] != null ? " · ${t['vehicle']}" : ""}',
                  style: const TextStyle(fontSize: 11.5, color: BuzUpColors.muted),
                ),
              ]),
            ),
            if (seats is int)
              Text('$seats lugares',
                  style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: BuzUpColors.muted)),
          ]),
        ),
      ),
    );
  }

  Widget _methodSelector() {
    Widget option(_PayMethod m, IconData icon, String title, String subtitle) {
      final selected = _method == m;
      final scheme = Theme.of(context).colorScheme;
      return Expanded(
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: _purchasing ? null : () => setState(() {
            _method = m;
            _error = null;
          }),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            decoration: BoxDecoration(
              color: selected ? BuzUpColors.navy : scheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: selected ? BuzUpColors.navy : scheme.outline),
            ),
            child: Column(children: [
              Icon(icon, size: 20, color: selected ? Colors.white : BuzUpColors.muted),
              const SizedBox(height: 4),
              Text(title,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12.5, fontWeight: FontWeight.w800,
                    color: selected ? Colors.white : null,
                  )),
              Text(subtitle,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 10.5,
                    color: selected ? Colors.white70 : BuzUpColors.muted,
                  )),
            ]),
          ),
        ),
      );
    }

    return Row(children: [
      option(_PayMethod.wallet, Icons.account_balance_wallet, 'Saldo BusUp', 'usa a carteira'),
      const SizedBox(width: 10),
      option(_PayMethod.mobileMoney, Icons.phone_iphone, 'M-Pesa / e-Mola', 'paga na hora'),
    ]);
  }

  Widget _currencySelector() {
    final codes = ['MZN', ..._rates.keys.toList()..sort()];
    return Row(children: [
      const Text('Ver precos em', style: TextStyle(fontSize: 12, color: BuzUpColors.muted)),
      const SizedBox(width: 10),
      ...codes.map((c) => Padding(
            padding: const EdgeInsets.only(right: 6),
            child: ChoiceChip(
              label: Text(c, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800)),
              selected: _currency == c,
              visualDensity: VisualDensity.compact,
              onSelected: (_) => setState(() => _currency = c),
            ),
          )),
    ]);
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
    // No pagamento directo o pacote nao entra: paga-se a tarifa cheia.
    final directPay = _method == _PayMethod.mobileMoney;
    final due = directPay ? base : walletAmount;
    final packageName = (_quote!['package_name'] ?? '').toString();
    final discountType = (_quote!['discount_type'] ?? '').toString();
    final hasPackage = !directPay && _quote!['package_id'] != null && packageName.isNotEmpty;
    final discount = (base - walletAmount).clamp(0, base);
    final fullyCoveredByPackage = walletAmount <= 0 && hasPackage;
    final rate = _rate;

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
        row('Tarifa base', _fmtMzn(base), icon: Icons.directions_bus),
        if (rate != null)
          row('Em $_currency (1 $_currency = ${rate.toStringAsFixed(2)} MZN)', _fmtDisplay(base),
              icon: Icons.currency_exchange),
        if (hasPackage) ...[
          const Divider(color: Colors.white24, height: 14),
          row('Pacote', packageName,
              color: BuzUpColors.orangeDark, bold: FontWeight.w900, icon: Icons.card_giftcard),
          if (discount > 0)
            row(_discountLabel(discountType), '-${_fmtMzn(discount.toDouble())}',
                color: const Color(0xFF6FE38B), icon: Icons.local_offer),
        ],
        const Divider(color: Colors.white24, height: 16),
        Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
          Expanded(
            child: Text(directPay ? 'A PAGAR POR M-PESA/E-MOLA' : 'A PAGAR DA CARTEIRA',
                style: const TextStyle(color: Colors.white, fontSize: 11.5, letterSpacing: 1.2, fontWeight: FontWeight.w900)),
          ),
          Text(_fmtMzn(due),
              style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900, letterSpacing: -0.3)),
        ]),
        if (rate != null) Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Align(
            alignment: Alignment.centerRight,
            child: Text('≈ ${_fmtDisplay(due)} · o debito e sempre em MZN',
                style: const TextStyle(color: Colors.white70, fontSize: 11)),
          ),
        ),
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
    final base = double.tryParse('${_quote!['base_fare'] ?? 0}') ?? 0;
    final walletAmount = double.tryParse('${_quote!['wallet_amount'] ?? 0}') ?? 0;
    if (_method == _PayMethod.mobileMoney) {
      final fmt = base.toStringAsFixed(2)
          .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+\.)'), (m) => '${m[1]} ');
      return 'PAGAR $fmt MZN COM M-PESA/E-MOLA';
    }
    if (walletAmount <= 0) return 'USAR PACOTE - GRATIS';
    final fmt = walletAmount.toStringAsFixed(2)
        .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+\.)'), (m) => '${m[1]} ');
    return 'PAGAR $fmt MZN';
  }
}
