import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../core/api_client.dart';
import '../../core/bus_loader.dart';
import '../../core/config.dart';
import '../../core/feedback.dart';
import '../../core/nfc.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

class SaleFlowScreen extends ConsumerStatefulWidget {
  const SaleFlowScreen({super.key});

  @override
  ConsumerState<SaleFlowScreen> createState() => _SaleFlowScreenState();
}

class _SaleFlowScreenState extends ConsumerState<SaleFlowScreen> {
  int _step = 0;
  List<dynamic> _trips = [];
  bool _loadingTrips = true;
  String? _error;

  Map<String, dynamic>? _selectedTrip;
  List<dynamic> _stops = [];
  int? _originId;
  int? _destinationId;
  Map<String, dynamic>? _fare;
  String _phone = '';
  int _quantity = 1;
  String _paymentMethod = 'mobile_money'; // or 'card'
  String? _cardUid;
  String? _qrToken;
  Map<String, dynamic>? _scannedCard;
  // Stable token per sale attempt so the same trip+phone tap isn't charged
  // twice if the agent double-presses or the network retries.
  String _idempotencyKey = '';

  String? _paymentRef;
  String? _saleRef;
  String _paymentStatus = '';
  Timer? _pollTimer;
  List<dynamic> _tickets = [];

  @override
  void initState() {
    super.initState();
    _loadTrips();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    NfcCardReader.stop();
    super.dispose();
  }

  Future<void> _loadTrips() async {
    setState(() {
      _loadingTrips = true;
      _error = null;
    });
    try {
      final api = ref.read(agentApiProvider);
      final trips = await api.trips();
      setState(() => _trips = trips);
    } on DioException catch (e) {
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _loadingTrips = false);
    }
  }

  Future<void> _selectTrip(Map<String, dynamic> trip) async {
    setState(() {
      _selectedTrip = trip;
      _error = null;
    });
    try {
      final detail = await ref.read(agentApiProvider).trip(trip['id'] as int);
      setState(() {
        _stops = (detail['stops'] as List?) ?? [];
        _step = 1;
      });
    } on DioException catch (e) {
      setState(() => _error = ApiClient.extractError(e));
    }
  }

  Future<void> _calculateFare() async {
    if (_originId == null || _destinationId == null) {
      setState(() => _error = 'Selecione origem e destino.');
      return;
    }
    if (_originId == _destinationId) {
      setState(() => _error = 'Origem e destino devem ser diferentes.');
      return;
    }
    setState(() {
      _error = null;
      _fare = null;
    });
    try {
      final api = ref.read(agentApiProvider);
      final fare = await api.quoteFare(
        tripId: _selectedTrip!['id'] as int,
        originStopId: _originId!,
        destinationStopId: _destinationId!,
      );
      setState(() {
        _fare = fare;
        _step = 2;
      });
    } on DioException catch (e) {
      setState(() => _error = ApiClient.extractError(e));
    }
  }

  Future<void> _requestPayment() async {
    if (_paymentMethod == 'mobile_money') {
      if (!RegExp(r'^[0-9]{9}$').hasMatch(_phone)) {
        setState(() => _error = 'Telefone deve ter 9 digitos.');
        return;
      }
    } else if (_paymentMethod == 'card') {
      final hasUid = _cardUid != null && _cardUid!.isNotEmpty;
      final hasQr = _qrToken != null && _qrToken!.isNotEmpty;
      if (!hasUid && !hasQr) {
        setState(() => _error = 'Aproxime o cartao ou leia o QR.');
        return;
      }
    }
    if (_idempotencyKey.isEmpty) {
      _idempotencyKey = DateTime.now().millisecondsSinceEpoch.toRadixString(36) +
          '-${_selectedTrip!['id']}-${_originId}-${_destinationId}-$_quantity';
    }
    setState(() {
      _error = null;
      _step = 3;
      _paymentStatus = 'pending';
    });
    try {
      final store = ref.read(secureStoreProvider);
      final serial = await store.getDeviceSerial();
      final api = ref.read(agentApiProvider);
      final res = await api.createSale(
        tripId: _selectedTrip!['id'] as int,
        originStopId: _originId!,
        destinationStopId: _destinationId!,
        paymentMethod: _paymentMethod,
        passengerPhone: _paymentMethod == 'mobile_money' ? _phone : null,
        cardUid: _paymentMethod == 'card' ? _cardUid : null,
        qrToken: _paymentMethod == 'card' ? _qrToken : null,
        quantity: _quantity,
        deviceSerial: serial,
        idempotencyKey: _idempotencyKey,
      );
      _saleRef = res['sale_reference'] as String?;
      final payment = res['payment'] as Map?;
      _paymentRef = payment?['reference'] as String?;
      _paymentStatus = (payment?['status'] as String?) ?? 'pending';

      if (_paymentStatus == 'confirmed') {
        // For card sales the response already brings tickets — surface them.
        final inlineTickets = res['tickets'];
        if (inlineTickets is List) {
          _tickets = inlineTickets;
        }
        await _afterConfirmed();
      } else if (_paymentStatus == 'failed') {
        setState(() => _error = (payment?['detail'] as String?) ?? 'Pagamento falhado.');
      } else {
        _startPolling();
      }
    } on DioException catch (e) {
      setState(() {
        _error = ApiClient.extractError(e);
        _step = 2;
      });
    }
    if (mounted) setState(() {});
  }

  void _startPolling() {
    final start = DateTime.now();
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(AppConfig.paymentPollInterval, (timer) async {
      if (_paymentRef == null) return;
      if (DateTime.now().difference(start) > AppConfig.paymentPollTimeout) {
        timer.cancel();
        if (mounted) setState(() => _error = 'Tempo esgotado a aguardar confirmacao.');
        return;
      }
      try {
        final st = await ref.read(agentApiProvider).paymentStatus(_paymentRef!);
        final status = (st['status'] as String?) ?? '';
        if (status != _paymentStatus) {
          setState(() => _paymentStatus = status);
        }
        if (status == 'confirmed') {
          timer.cancel();
          setState(() => _tickets = (st['tickets'] as List?) ?? []);
          await _afterConfirmed();
        } else if (status == 'failed' || status == 'expired' || status == 'cancelled') {
          timer.cancel();
          setState(() => _error = 'Pagamento $status.');
        }
      } on DioException catch (e) {
        // Transient network errors are fine — keep polling. Other 4xx/5xx
        // surface as a banner without aborting the timer (next tick retries).
        final code = e.response?.statusCode;
        if (code != null && code >= 400 && code < 500 && code != 408 && code != 429) {
          timer.cancel();
          if (mounted) setState(() => _error = ApiClient.extractError(e));
        }
      } catch (e) {
        debugPrint('payment poll error: $e');
      }
    });
  }

  Future<void> _afterConfirmed() async {
    if (_paymentRef == null) return;
    try {
      final st = await ref.read(agentApiProvider).paymentStatus(_paymentRef!);
      setState(() {
        _tickets = (st['tickets'] as List?) ?? [];
        _step = 4;
      });
    } on DioException catch (e) {
      if (mounted) setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      debugPrint('after-confirmed error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Venda · passo ${_step + 1} de 5'),
        backgroundColor: const Color(0xFF071E49),
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: _buildStep(),
        ),
      ),
    );
  }

  Widget _buildStep() {
    if (_error != null) {
      // Error banner is shown inline at the top of each step
    }
    switch (_step) {
      case 0:
        return _stepSelectTrip();
      case 1:
        return _stepSelectStops();
      case 2:
        return _stepPhoneAndConfirm();
      case 3:
        return _stepWaitPayment();
      case 4:
        return _stepDone();
    }
    return const SizedBox.shrink();
  }

  Widget _errorBanner() {
    if (_error == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: Colors.red.shade100, borderRadius: BorderRadius.circular(8)),
        child: Row(children: [
          const Icon(Icons.error_outline, color: Colors.red),
          const SizedBox(width: 8),
          Expanded(child: Text(_error!, style: const TextStyle(color: Colors.red))),
        ]),
      ),
    );
  }

  Widget _stepSelectTrip() {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _errorBanner(),
      const Text('1. Escolha a viagem', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      const SizedBox(height: 12),
      Expanded(
        child: _loadingTrips
            ? const Center(child: CircularProgressIndicator())
            : _trips.isEmpty
                ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    const Icon(Icons.no_transfer, size: 48, color: Colors.grey),
                    const SizedBox(height: 8),
                    const Text('Nenhuma viagem disponivel.'),
                    TextButton(onPressed: _loadTrips, child: const Text('Actualizar')),
                  ]))
                : ListView.separated(
                    itemCount: _trips.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final t = _trips[i] as Map<String, dynamic>;
                      return Card(
                        child: ListTile(
                          leading: const Icon(Icons.directions_bus, color: Color(0xFFE47B11)),
                          title: Text('${t['route_code']} - ${t['route_name']}'),
                          subtitle: Text('${t['vehicle']} · motorista: ${t['driver']}'),
                          trailing: Chip(label: Text(t['status'] ?? '', style: const TextStyle(fontSize: 10))),
                          onTap: () => _selectTrip(t),
                        ),
                      );
                    },
                  ),
      ),
    ]);
  }

  Widget _stepSelectStops() {
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _errorBanner(),
        Text(_selectedTrip != null ? '2. ${_selectedTrip!['route_code']} - ${_selectedTrip!['route_name']}' : '', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        DropdownButtonFormField<int>(
          decoration: const InputDecoration(labelText: 'Origem', prefixIcon: Icon(Icons.location_on)),
          value: _originId,
          items: _stops.where((s) => s['id'] != _destinationId).map((s) {
            final st = s as Map<String, dynamic>;
            return DropdownMenuItem(value: st['id'] as int, child: Text(st['name'] ?? ''));
          }).toList(),
          onChanged: (v) => setState(() => _originId = v),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<int>(
          decoration: const InputDecoration(labelText: 'Destino', prefixIcon: Icon(Icons.location_on, color: Color(0xFFE47B11))),
          value: _destinationId,
          items: _stops.where((s) => s['id'] != _originId).map((s) {
            final st = s as Map<String, dynamic>;
            return DropdownMenuItem(value: st['id'] as int, child: Text(st['name'] ?? ''));
          }).toList(),
          onChanged: (v) => setState(() => _destinationId = v),
        ),
        const SizedBox(height: 24),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE47B11), minimumSize: const Size.fromHeight(50)),
          onPressed: _calculateFare,
          child: const Text('CALCULAR TARIFA', style: TextStyle(fontWeight: FontWeight.bold)),
        ),
        TextButton(onPressed: () => setState(() => _step = 0), child: const Text('Voltar')),
      ]),
    );
  }

  Widget _stepPhoneAndConfirm() {
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _errorBanner(),
        const Text('3. Telefone do passageiro', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Card(
          color: const Color(0xFFFFF8E1),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_selectedTrip!['route_code']} - ${_selectedTrip!['route_name']}'),
              Text('${_fare!['origin']} → ${_fare!['destination']}'),
              const Divider(),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                const Text('Preco unit.'),
                Text('${_fare!['fare_amount']} MZN', style: const TextStyle(fontWeight: FontWeight.bold)),
              ]),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                const Text('Quantidade'),
                Row(children: [
                  IconButton(icon: const Icon(Icons.remove), onPressed: _quantity > 1 ? () => setState(() => _quantity--) : null),
                  Text('$_quantity', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  IconButton(icon: const Icon(Icons.add), onPressed: _quantity < 10 ? () => setState(() => _quantity++) : null),
                ]),
              ]),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                const Text('TOTAL', style: TextStyle(fontWeight: FontWeight.bold)),
                Text(
                  '${(double.parse(_fare!['fare_amount'].toString()) * _quantity).toStringAsFixed(2)} MZN',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: Color(0xFFE47B11)),
                ),
              ]),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        _methodPicker(),
        const SizedBox(height: 10),
        if (_paymentMethod == 'mobile_money')
          TextField(
            keyboardType: TextInputType.phone,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly, LengthLimitingTextInputFormatter(9)],
            decoration: const InputDecoration(
              labelText: 'Telefone (9 digitos)',
              prefixIcon: Icon(Icons.phone),
              hintText: '84/85/86/87...',
            ),
            onChanged: (v) => _phone = v,
          )
        else
          _cardCapturePanel(),
        const SizedBox(height: 18),
        FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE47B11), minimumSize: const Size.fromHeight(54)),
          icon: Icon(_paymentMethod == 'card' ? Icons.credit_card : Icons.payment),
          label: Text(
            _paymentMethod == 'card' ? 'COBRAR DO CARTAO' : 'SOLICITAR PAGAMENTO',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          onPressed: _requestPayment,
        ),
        TextButton(onPressed: () => setState(() => _step = 1), child: const Text('Voltar')),
      ]),
    );
  }

  Widget _stepWaitPayment() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardBg = isDark ? const Color(0xFF1A1F26) : Colors.white;
    final border = isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4);
    final fg = isDark ? Colors.white : const Color(0xFF15191E);
    final muted = isDark ? Colors.white60 : const Color(0xFF6B6356);

    if (_error != null) {
      return SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          _errorBanner(),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () { _pollTimer?.cancel(); setState(() { _error = null; _step = 2; }); },
            child: const Text('Voltar'),
          ),
        ]),
      );
    }

    final isConfirmed = _paymentStatus == 'confirmed';
    final isFailed = _paymentStatus == 'failed';
    final statusColor = isConfirmed
        ? BuzUpColors.success
        : isFailed
            ? BuzUpColors.danger
            : BuzUpColors.orange;
    final statusLabel = isConfirmed
        ? 'CONFIRMADO'
        : isFailed
            ? 'FALHADO'
            : 'A AGUARDAR';

    return LayoutBuilder(builder: (ctx, c) {
      return SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: c.maxHeight),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const SizedBox(height: 8),
              // Bus animation
              Center(
                child: BusLoader(
                  size: 180,
                  label: isConfirmed
                      ? 'Pagamento confirmado!'
                      : isFailed
                          ? 'Pagamento nao concluido'
                          : 'A aguardar confirmacao do passageiro',
                ),
              ),
              const SizedBox(height: 14),
              // Status pill + reference
              Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: statusColor.withValues(alpha: 0.40)),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Container(width: 8, height: 8, decoration: BoxDecoration(color: statusColor, shape: BoxShape.circle)),
                    const SizedBox(width: 8),
                    Text(statusLabel,
                        style: TextStyle(color: statusColor, fontWeight: FontWeight.w800, letterSpacing: 0.6)),
                  ]),
                ),
              ),
              const SizedBox(height: 14),
              // Operation summary card
              Container(
                decoration: BoxDecoration(
                  color: cardBg,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: border),
                ),
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  _kv('Rota', '${_selectedTrip?['route_code'] ?? '-'} - ${_selectedTrip?['route_name'] ?? ''}', fg, muted),
                  const Divider(height: 14),
                  _kv('Origem', _stopName(_originId), fg, muted),
                  _kv('Destino', _stopName(_destinationId), fg, muted),
                  const Divider(height: 14),
                  _kv('Tarifa unitaria', '${_fare?['unit_amount'] ?? '0.00'} MZN', fg, muted),
                  _kv('Quantidade', 'x$_quantity', fg, muted),
                  const Divider(height: 14),
                  Row(children: [
                    Expanded(child: Text('TOTAL A COBRAR',
                        style: TextStyle(color: muted, fontSize: 11.5, letterSpacing: 1.0, fontWeight: FontWeight.w700))),
                    Text('${_fare?['total_amount'] ?? '0.00'} MZN',
                        style: TextStyle(color: fg, fontSize: 20, fontWeight: FontWeight.w800)),
                  ]),
                  const SizedBox(height: 10),
                  // Phone being charged
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: BuzUpColors.orange.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: BuzUpColors.orange.withValues(alpha: 0.30)),
                    ),
                    child: Row(children: [
                      const Icon(Icons.phone_iphone, color: BuzUpColors.orange, size: 22),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('A COBRAR EM',
                              style: TextStyle(color: muted, fontSize: 10.5, letterSpacing: 1.0, fontWeight: FontWeight.w700)),
                          const SizedBox(height: 2),
                          Text(_maskPhone(_phone),
                              style: TextStyle(color: fg, fontSize: 16, fontWeight: FontWeight.w800, letterSpacing: 0.4)),
                        ]),
                      ),
                    ]),
                  ),
                  if (_paymentRef != null) ...[
                    const SizedBox(height: 10),
                    Text('Ref: $_paymentRef', style: TextStyle(color: muted, fontSize: 11)),
                  ],
                ]),
              ),
              const SizedBox(height: 14),
              if (!isConfirmed && !isFailed)
                TextButton.icon(
                  icon: const Icon(Icons.refresh),
                  label: const Text('Actualizar agora'),
                  onPressed: () async {
                    if (_paymentRef == null) return;
                    try {
                      final st = await ref.read(agentApiProvider).paymentStatus(_paymentRef!);
                      final s = (st['status'] as String?) ?? _paymentStatus;
                      setState(() => _paymentStatus = s);
                      if (s == 'confirmed') {
                        await AppFeedback.success();
                        await _afterConfirmed();
                      } else if (s == 'failed') {
                        await AppFeedback.error();
                      }
                    } on DioException catch (e) {
                      if (mounted) setState(() => _error = ApiClient.extractError(e));
                    } catch (e) {
                      debugPrint('manual refresh error: $e');
                    }
                  },
                ),
              const SizedBox(height: 8),
            ]),
          ),
        ),
      );
    });
  }

  Widget _methodPicker() {
    return LayoutBuilder(builder: (ctx, c) {
      Widget tile(String key, IconData icon, String label) {
        final selected = _paymentMethod == key;
        return Expanded(
          child: GestureDetector(
            onTap: () async {
              if (key == 'card') {
                await _startCardScan();
              } else {
                await NfcCardReader.stop();
              }
              setState(() {
                _paymentMethod = key;
                _error = null;
                if (key != 'card') {
                  _cardUid = null;
                  _scannedCard = null;
                }
              });
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              margin: const EdgeInsets.symmetric(horizontal: 3),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              decoration: BoxDecoration(
                color: selected ? BuzUpColors.orange : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: selected ? BuzUpColors.orange : Colors.grey.shade400),
              ),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(icon, color: selected ? Colors.white : Colors.grey, size: 18),
                const SizedBox(width: 6),
                Text(label,
                    style: TextStyle(
                      color: selected ? Colors.white : Colors.grey.shade700,
                      fontWeight: FontWeight.w800, fontSize: 12.5, letterSpacing: 0.4,
                    )),
              ]),
            ),
          ),
        );
      }
      return Row(children: [
        tile('mobile_money', Icons.phone_iphone, 'M-Pesa / E-Mola'),
        tile('card', Icons.credit_card, 'Cartao NFC'),
      ]);
    });
  }

  Future<void> _startCardScan() async {
    try {
      await NfcCardReader.startStream((uid) async {
        await AppFeedback.softBeep();
        // Lookup the card to surface passenger + balance
        Map<String, dynamic>? data;
        try {
          final res = await ref.read(agentApiProvider).cardLookup(cardUid: uid);
          data = (res['card'] as Map?)?.cast<String, dynamic>();
        } on DioException catch (e) {
          // Lookup failure shouldn't block the sale (backend re-validates),
          // but we surface the message so the agent knows the card isn't
          // registered yet / is blocked / passenger has no wallet etc.
          if (mounted) setState(() => _error = ApiClient.extractError(e));
        } catch (e) {
          debugPrint('card lookup error: $e');
        }
        if (!mounted) return;
        setState(() {
          _cardUid = uid;
          _scannedCard = data;
          _error = null;
        });
      });
    } on NfcUnavailableException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  Future<void> _openQrSheet() async {
    final qr = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const _QrScannerSheet()),
    );
    if (qr == null || qr.isEmpty || !mounted) return;
    // Stop the NFC reader while we look the card up via QR.
    await NfcCardReader.stop();
    setState(() {
      _qrToken = qr;
      _cardUid = null;
      _error = null;
    });
    try {
      final res = await ref.read(agentApiProvider).cardLookup(qrToken: qr);
      final data = (res['card'] as Map?)?.cast<String, dynamic>();
      if (!mounted) return;
      setState(() => _scannedCard = data);
    } on DioException catch (e) {
      if (mounted) setState(() => _error = ApiClient.extractError(e));
    }
  }

  Widget _cardCapturePanel() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fg = isDark ? Colors.white : const Color(0xFF15191E);
    final muted = isDark ? Colors.white60 : const Color(0xFF6B6356);
    final cardBg = isDark ? const Color(0xFF1A1F26) : Colors.white;
    final border = isDark ? const Color(0xFF252B33) : const Color(0xFFE7E1D4);
    final scanned = _scannedCard;
    final hasIdentifier = _cardUid != null || _qrToken != null;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Container(
            width: 38, height: 38,
            decoration: BoxDecoration(
              color: BuzUpColors.orange.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(9),
            ),
            child: Icon(
              _qrToken != null ? Icons.qr_code : Icons.nfc,
              color: BuzUpColors.orange, size: 20,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(
                hasIdentifier
                    ? (_qrToken != null ? 'QR digital detectado' : 'Cartao detectado')
                    : 'Aproxime o cartao ou leia o QR',
                style: TextStyle(color: fg, fontSize: 13, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 2),
              Text(
                hasIdentifier
                    ? (_cardUid ?? 'QR ${_qrToken!.substring(0, _qrToken!.length.clamp(0, 14))}...')
                    : 'O valor sera debitado do saldo do passageiro.',
                maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                style: TextStyle(color: muted, fontSize: 11, fontFamily: _cardUid != null ? 'monospace' : null),
              ),
            ]),
          ),
          IconButton(
            tooltip: 'Ler QR do cartao digital',
            icon: const Icon(Icons.qr_code_scanner, color: BuzUpColors.orange),
            onPressed: _openQrSheet,
          ),
        ]),
        if (scanned != null) ...[
          const SizedBox(height: 10),
          Divider(height: 1, color: border),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(
                  scanned['passenger_name']?.toString().isNotEmpty == true
                      ? scanned['passenger_name'].toString()
                      : 'Sem passageiro',
                  maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                  style: TextStyle(color: fg, fontSize: 13, fontWeight: FontWeight.w700),
                ),
                Text(
                  '${scanned['card_number']} · ${scanned['passenger_phone_masked'] ?? '-'}',
                  maxLines: 1, overflow: TextOverflow.fade, softWrap: false,
                  style: TextStyle(color: muted, fontSize: 11),
                ),
              ]),
            ),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text(
                '${(scanned['wallet'] as Map?)?['balance'] ?? '0.00'} MZN',
                style: TextStyle(color: fg, fontSize: 15, fontWeight: FontWeight.w800),
              ),
              Text('Saldo disponivel', style: TextStyle(color: muted, fontSize: 9.5)),
            ]),
          ]),
        ],
      ]),
    );
  }

  Widget _kv(String k, String v, Color fg, Color muted) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(children: [
        Expanded(child: Text(k, style: TextStyle(color: muted, fontSize: 12))),
        Flexible(
          child: Text(v,
              maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.right,
              style: TextStyle(color: fg, fontSize: 13.5, fontWeight: FontWeight.w700)),
        ),
      ]),
    );
  }

  String _maskPhone(String phone) {
    final digits = phone.replaceAll(RegExp(r'\D'), '');
    if (digits.length < 4) return digits;
    return '***${digits.substring(digits.length - 4)}';
  }

  String _stopName(int? id) {
    if (id == null) return '-';
    final hit = _stops.firstWhere(
      (e) => (e is Map) && (e['id'] == id),
      orElse: () => null,
    );
    if (hit is Map && hit['name'] is String) return hit['name'] as String;
    return '-';
  }

  Widget _stepDone() {
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Icon(Icons.check_circle, color: Colors.green, size: 64),
        const SizedBox(height: 8),
        const Center(child: Text('VENDA CONFIRMADA', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.green))),
        const SizedBox(height: 8),
        Center(child: Text('Ref: ${_saleRef ?? '-'}')),
        const SizedBox(height: 12),
        const Text('Bilhetes emitidos:', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        ..._tickets.map((t) {
          final tt = t as Map<String, dynamic>;
          return Card(
            child: ListTile(
              dense: true,
              leading: const Icon(Icons.confirmation_number, color: Color(0xFFE47B11)),
              title: Text('${tt['reference']}'),
              subtitle: Text('${tt['route_code']} · ${tt['origin_stop']} → ${tt['destination_stop']} · ${tt['fare_amount']} MZN'),
              trailing: const Text('ACTIVO', style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold, fontSize: 11)),
            ),
          );
        }),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF1FB04A).withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF1FB04A).withValues(alpha: 0.4)),
          ),
          child: const Row(children: [
            Icon(Icons.sms, color: Color(0xFF1FB04A)),
            SizedBox(width: 10),
            Expanded(child: Text(
              'Bilhete enviado por SMS ao passageiro.',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5),
            )),
          ]),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE47B11), minimumSize: const Size.fromHeight(50)),
          icon: const Icon(Icons.add),
          label: const Text('NOVA VENDA'),
          onPressed: () => setState(() {
            _step = 0;
            _selectedTrip = null;
            _stops = [];
            _originId = null;
            _destinationId = null;
            _fare = null;
            _phone = '';
            _quantity = 1;
            _paymentMethod = 'mobile_money';
            _cardUid = null;
            _qrToken = null;
            _scannedCard = null;
            _idempotencyKey = '';
            _paymentRef = null;
            _saleRef = null;
            _paymentStatus = '';
            _tickets = [];
            _error = null;
          }),
        ),
        TextButton(onPressed: () => context.go('/home'), child: const Text('Voltar ao inicio')),
      ]),
    );
  }
}

/// Lightweight full-screen QR scanner used inside the sale flow. Returns the
/// scanned raw value via `Navigator.pop(context, value)`.
class _QrScannerSheet extends StatefulWidget {
  const _QrScannerSheet();

  @override
  State<_QrScannerSheet> createState() => _QrScannerSheetState();
}

class _QrScannerSheetState extends State<_QrScannerSheet> {
  final _controller = MobileScannerController(detectionSpeed: DetectionSpeed.noDuplicates);
  bool _done = false;
  bool _torch = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Ler QR do cartao digital'),
        actions: [
          IconButton(
            icon: Icon(_torch ? Icons.flash_on : Icons.flash_off),
            onPressed: () async {
              await _controller.toggleTorch();
              setState(() => _torch = !_torch);
            },
          ),
        ],
      ),
      body: Stack(children: [
        MobileScanner(
          controller: _controller,
          onDetect: (capture) {
            if (_done) return;
            final raw = capture.barcodes.first.rawValue;
            if (raw == null || raw.isEmpty) return;
            _done = true;
            Navigator.pop(context, raw);
          },
        ),
        Center(
          child: Container(
            width: 240, height: 240,
            decoration: BoxDecoration(
              border: Border.all(color: BuzUpColors.orange, width: 3),
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ]),
    );
  }
}
