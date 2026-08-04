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
import '../../core/idempotency.dart';
import '../../core/labels.dart';
import '../../core/nfc.dart';
import '../../core/providers.dart';
import '../../core/seat_map_screen.dart';
import '../../core/stop_picker.dart';
import '../../core/theme.dart';

/// Os passos da venda ao balcao.
///
/// `seats` so existe nas rotas que marcam lugar (interprovincial e
/// internacional). Numa carreira urbana a venda tem tres passos — viagem,
/// trajecto e pagamento — porque nao ha lugar a escolher.
///
/// `processing` e `done` nao sao escolhas do agente: sao o que acontece depois
/// de cobrar. Por isso nao contam na barra de progresso.
enum _Step { trip, route, seats, payment, processing, done }

class SaleFlowScreen extends ConsumerStatefulWidget {
  const SaleFlowScreen({super.key});

  @override
  ConsumerState<SaleFlowScreen> createState() => _SaleFlowScreenState();
}

class _SaleFlowScreenState extends ConsumerState<SaleFlowScreen> {
  _Step _step = _Step.trip;
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
  /// Impede que uma venda repetida por falha de rede seja cobrada duas vezes.
  final _idem = IdempotencyScope();

  String? _paymentRef;
  String? _saleRef;
  String _paymentStatus = '';
  Timer? _pollTimer;
  List<dynamic> _tickets = [];

  // Moeda de exibicao (rand nas rotas p/ Africa do Sul). So visual — a
  // cobranca e sempre em MZN; a escolha fica registada no bilhete.
  Map<String, double> _rates = const {};
  String _currency = 'MZN';

  // Planta de lugares: so existe nas rotas que marcam lugar (interprovincial
  // e internacional). Nas urbanas vem vazia e o passo nem aparece.
  Map<String, dynamic>? _seatMap;
  final List<String> _pickedSeats = [];
  // Contacto de emergencia: obrigatorio nas mesmas rotas que marcam lugar
  // (interprovincial/internacional). Vai para o manifesto de bordo — o agente
  // ao balcao e quem tem o passageiro a frente para perguntar.
  final _emergNameCtrl = TextEditingController();
  final _emergPhoneCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadTrips();
    ref.read(agentApiProvider).exchangeRates().then((d) {
      final parsed = <String, double>{};
      (d['rates'] as Map?)?.forEach((k, v) {
        final n = double.tryParse('$v');
        if (n != null && n > 0) parsed['$k'] = n;
      });
      if (mounted) setState(() => _rates = parsed);
    }).catchError((_) {});
  }

  double? get _rate => _currency == 'MZN' ? null : _rates[_currency];

  /// A rota desta partida marca lugar? Quem decide e o backend (tipo de
  /// servico da rota) — o agente nao responde a nenhuma pergunta sobre isso.
  bool get _seatsRequired => _seatMap?['has_seat_map'] == true;

  String _inDisplay(num mzn) {
    final r = _rate;
    if (r == null) return '';
    return '${(mzn / r).toStringAsFixed(2)} $_currency';
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    NfcCardReader.stop();
    _emergNameCtrl.dispose();
    _emergPhoneCtrl.dispose();
    super.dispose();
  }

  /// Limpa TUDO o que pertencia a venda anterior.
  ///
  /// O passageiro seguinte e outra pessoa. O contacto de emergencia ficava no
  /// ecra depois de uma venda — os controladores de texto sobrevivem aos
  /// rebuilds — e, se o agente nao reparasse, o familiar do passageiro
  /// anterior seguia no manifesto de bordo do seguinte. O mesmo valia para a
  /// moeda de exibicao, que fica congelada no bilhete.
  ///
  /// Escrito como um metodo unico, e nao espalhado pelo botao, para nao voltar
  /// a esquecer um campo quando se acrescentar o proximo.
  void _resetSale() {
    _emergNameCtrl.clear();
    _emergPhoneCtrl.clear();
    setState(() {
      _step = _Step.trip;
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
      _seatMap = null;
      _pickedSeats.clear();
      _currency = 'MZN';
      _idem.rotate();
      _paymentRef = null;
      _saleRef = null;
      _paymentStatus = '';
      _tickets = [];
      _error = null;
    });
    // A venda que acabou de ser feita mudou a lotacao: recarregar evita
    // oferecer lugares que ja nao existem.
    _loadTrips();
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
        _seatMap = (detail['seat_map'] as Map?)?.cast<String, dynamic>();
        _pickedSeats.clear();
        _step = _Step.route;
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
        // Numa rota com lugar marcado o passo seguinte e a planta; numa
        // carreira urbana passa-se directo ao pagamento.
        _step = _seatsRequired ? _Step.seats : _Step.payment;
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
    setState(() {
      _error = null;
      _step = _Step.processing;
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
        displayCurrency: _currency,
        seats: _seatsRequired ? List<String>.from(_pickedSeats) : const [],
        emergencyName: _seatsRequired ? _emergNameCtrl.text.trim() : '',
        emergencyPhone: _seatsRequired ? _emergPhoneCtrl.text.trim() : '',
        // A assinatura inclui tudo o que define a venda: se o agente voltar
        // atras e corrigir o destino ou a quantidade, a chave roda sozinha e a
        // venda seguinte nao e confundida com a anterior.
        idempotencyKey: _idem.keyFor(
          'sale:${_selectedTrip!['id']}:$_originId:$_destinationId:$_quantity'
          ':$_paymentMethod:$_phone:${_cardUid ?? _qrToken ?? ''}:$_currency'
          ':${_pickedSeats.join(",")}',
        ),
      );
      // O servidor respondeu: a venda seguinte e nova e leva chave nova.
      _idem.rotate();
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
      // Timeout ou 5xx: a venda pode ter sido criada no servidor. Mantem-se a
      // chave para que a repeticao devolva essa venda em vez de criar outra.
      if (!isAmbiguousFailure(e)) _idem.rotate();
      setState(() {
        _error = ApiClient.extractError(e);
        _step = _Step.payment;
      });
      // Se o lugar entretanto foi vendido por outro agente, a planta que esta
      // no ecra ja mente. Recarrega-la evita o agente insistir no mesmo lugar.
      if (_seatsRequired && (_error ?? '').toLowerCase().contains('ocupado')) {
        await _refreshSeatMap();
      }
    }
    if (mounted) setState(() {});
  }

  /// Recarrega a planta e larga os lugares que entretanto ficaram ocupados.
  Future<void> _refreshSeatMap() async {
    final trip = _selectedTrip;
    if (trip == null) return;
    try {
      final detail = await ref.read(agentApiProvider).trip(trip['id'] as int);
      final map = (detail['seat_map'] as Map?)?.cast<String, dynamic>();
      if (map == null || !mounted) return;
      final taken = <String>{
        for (final row in (map['rows'] as List? ?? const []))
          for (final side in ['left', 'right'])
            for (final s in ((row as Map)[side] as List? ?? const []))
              if ((s as Map)['occupied'] == true) s['label'].toString(),
      };
      setState(() {
        _seatMap = map;
        _pickedSeats.removeWhere(taken.contains);
      });
    } catch (_) {
      // Falhar a recarregar a planta nao pode esconder o erro da venda.
    }
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
        _step = _Step.done;
      });
    } on DioException catch (e) {
      if (mounted) setState(() => _error = ApiClient.extractError(e));
    } catch (e) {
      debugPrint('after-confirmed error: $e');
    }
  }

  // --- estrutura do ecra ----------------------------------------------------

  /// Os passos de escolha desta venda, por ordem. Sem `processing`/`done`:
  /// esses acontecem, nao se escolhem.
  List<String> get _stepLabels => _seatsRequired
      ? const ['Viagem', 'Trajecto', 'Lugares', 'Pagamento']
      : const ['Viagem', 'Trajecto', 'Pagamento'];

  int get _stepIndex => switch (_step) {
        _Step.trip => 0,
        _Step.route => 1,
        _Step.seats => 2,
        _Step.payment => _seatsRequired ? 3 : 2,
        _ => _stepLabels.length - 1,
      };

  bool get _showsProgress => _step != _Step.processing && _step != _Step.done;

  void _goTo(_Step s) {
    FocusScope.of(context).unfocus();
    setState(() {
      _step = s;
      _error = null;
    });
  }

  /// Recuar um passo. Devolve false no primeiro — ai quem chama sai da venda.
  bool _back() {
    switch (_step) {
      case _Step.trip:
        return false;
      case _Step.route:
        _goTo(_Step.trip);
        return true;
      case _Step.seats:
        _goTo(_Step.route);
        return true;
      case _Step.payment:
        _goTo(_seatsRequired ? _Step.seats : _Step.route);
        return true;
      case _Step.processing:
      case _Step.done:
        // A meio de um pagamento nao se recua: o dinheiro ja esta a caminho.
        return true;
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _step == _Step.trip,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(_appBarTitle()),
          backgroundColor: const Color(0xFF071E49),
          foregroundColor: Colors.white,
          leading: _step == _Step.processing || _step == _Step.done
              ? const SizedBox.shrink()
              : IconButton(
                  icon: Icon(_step == _Step.trip ? Icons.close : Icons.arrow_back),
                  onPressed: () {
                    if (_back()) return;
                    context.canPop() ? context.pop() : context.go('/home');
                  },
                ),
        ),
        // O passo dos lugares nao tem campos de texto e precisa da altura toda
        // para calcular o tamanho do banco. Deixar o teclado (aberto no passo
        // anterior) encolher o ecra fazia a planta aparecer pequena.
        resizeToAvoidBottomInset: _step != _Step.seats,
        body: SafeArea(
          child: Column(children: [
            if (_showsProgress) _stepHeader(),
            Expanded(
              child: Padding(
                padding: EdgeInsets.fromLTRB(
                  16, 12, 16, _step == _Step.seats ? 0 : 12),
                child: _buildStep(),
              ),
            ),
            _bottomBar(),
          ]),
        ),
      ),
    );
  }

  String _appBarTitle() => switch (_step) {
        _Step.trip => 'Nova venda',
        _Step.route => 'Trajecto',
        _Step.seats => 'Escolha dos lugares',
        _Step.payment => 'Pagamento',
        _Step.processing => 'A processar',
        _Step.done => 'Venda concluida',
      };

  /// Barra de progresso segmentada. Igual a da app do passageiro: diz onde se
  /// esta e quanto falta, sem legendas que estouram num ecra estreito.
  Widget _stepHeader() {
    final labels = _stepLabels;
    final current = _stepIndex;
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('PASSO ${current + 1} DE ${labels.length}',
              style: const TextStyle(
                  fontSize: 10.5, letterSpacing: 1.4,
                  fontWeight: FontWeight.w800, color: Color(0xFF6B7A8F))),
          const Spacer(),
          Text(labels[current],
              style: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w900, color: Color(0xFF071E49))),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          for (var i = 0; i < labels.length; i++) ...[
            if (i > 0) const SizedBox(width: 6),
            Expanded(
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 220),
                height: 4,
                decoration: BoxDecoration(
                  color: i <= current ? const Color(0xFF1D5FA7) : const Color(0xFFDDE5EF),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ],
        ]),
      ]),
    );
  }

  Widget _buildStep() {
    switch (_step) {
      case _Step.trip:
        return _stepSelectTrip();
      case _Step.route:
        return _stepSelectStops();
      case _Step.seats:
        return _stepSeats();
      case _Step.payment:
        return _stepPhoneAndConfirm();
      case _Step.processing:
        return _stepWaitPayment();
      case _Step.done:
        return _stepDone();
    }
  }

  /// O que falta para avancar deste passo, em palavras. Vazio = pode avancar.
  ///
  /// Um botao cinzento sem explicacao deixa o agente parado com o passageiro
  /// a frente, sem saber o que fazer.
  String _missingForStep() {
    switch (_step) {
      case _Step.route:
        if (_originId == null) return 'Escolha a origem.';
        if (_destinationId == null) return 'Escolha o destino.';
        if (_originId == _destinationId) return 'Origem e destino devem ser diferentes.';
        if (_seatsRequired && _emergPhoneCtrl.text.trim().length != 9) {
          return 'Indique o contacto de emergencia (9 digitos).';
        }
        return '';
      case _Step.seats:
        final f = _quantity - _pickedSeats.length;
        if (f > 0) return 'Escolha mais $f lugar${f == 1 ? '' : 'es'}.';
        if (f < 0) return 'Escolheu lugares a mais.';
        return '';
      case _Step.payment:
        // Rede de seguranca: chegado aqui os lugares e o contacto ja estao
        // completos, mas se um dia deixarem de estar e melhor o botao dizer
        // do que a venda ser recusada pelo servidor com o passageiro a frente.
        final falta = _missingForSale();
        if (falta.isNotEmpty) return falta;
        if (_paymentMethod == 'mobile_money' &&
            !RegExp(r'^[0-9]{9}$').hasMatch(_phone)) {
          return 'Indique o telefone do passageiro (9 digitos).';
        }
        if (_paymentMethod == 'card' &&
            (_cardUid ?? '').isEmpty &&
            (_qrToken ?? '').isEmpty) {
          return 'Aproxime o cartao ou leia o QR.';
        }
        return '';
      default:
        return '';
    }
  }

  String _actionLabel() {
    switch (_step) {
      case _Step.route:
        return _seatsRequired ? 'ESCOLHER LUGARES' : 'CONTINUAR';
      case _Step.seats:
        return _pickedSeats.length == _quantity
            ? 'AVANCAR COM ${_pickedSeats.join(", ")}'
            : 'ESCOLHA OS LUGARES';
      case _Step.payment:
        return _paymentMethod == 'card' ? 'COBRAR DO CARTAO' : 'SOLICITAR PAGAMENTO';
      default:
        return '';
    }
  }

  void _onAction() {
    switch (_step) {
      case _Step.route:
        _calculateFare();
      case _Step.seats:
        _goTo(_Step.payment);
      case _Step.payment:
        _requestPayment();
      default:
        break;
    }
  }

  /// Barra fixa no fundo: a accao do passo esta SEMPRE visivel, sem rolar.
  ///
  /// Nos passos que nao tem accao (escolher a viagem, aguardar o pagamento,
  /// venda feita) nao aparece de todo — uma barra vazia so rouba ecra.
  Widget _bottomBar() {
    const semAccao = {_Step.trip, _Step.processing, _Step.done};
    if (semAccao.contains(_step)) return const SizedBox.shrink();
    final missing = _missingForStep();
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Color(0xFFE4EBF3))),
      ),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        if (missing.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(children: [
              const Icon(Icons.info_outline, size: 16, color: Color(0xFFB07B24)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(missing,
                    style: const TextStyle(
                        fontSize: 12.5, color: Color(0xFFB07B24),
                        fontWeight: FontWeight.w600)),
              ),
            ]),
          ),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF1D5FA7),
              minimumSize: const Size.fromHeight(52),
            ),
            icon: Icon(switch (_step) {
              _Step.route => Icons.arrow_forward,
              _Step.seats => Icons.event_seat,
              _ => _paymentMethod == 'card' ? Icons.credit_card : Icons.payment,
            }),
            label: Text(_actionLabel(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            onPressed: missing.isEmpty ? _onAction : null,
          ),
        ),
      ]),
    );
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
                          leading: const Icon(Icons.directions_bus, color: Color(0xFF1D5FA7)),
                          title: Text('${t['route_code']} - ${t['route_name']}'),
                          subtitle: Text('${t['vehicle']} · motorista: ${t['driver']}'),
                          trailing: Chip(label: Text(tripStatusLabel((t['status'] ?? '').toString()), style: const TextStyle(fontSize: 10))),
                          onTap: () => _selectTrip(t),
                        ),
                      );
                    },
                  ),
      ),
    ]);
  }

  /// Passo 2: de onde para onde, quantos bilhetes e — nas rotas longas — o
  /// contacto de emergencia.
  ///
  /// A quantidade vive aqui, e nao no pagamento como antes, porque e ela que
  /// diz quantos lugares ha para escolher no passo seguinte. Pedi-la depois
  /// obrigava a voltar atras a meio da escolha da planta.
  Widget _stepSelectStops() {
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _errorBanner(),
        if (_selectedTrip != null)
          Text('${_selectedTrip!['route_code']} - ${_selectedTrip!['route_name']}',
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        StopPickerField(
          label: 'Origem',
          icon: const Icon(Icons.location_on),
          stops: _stops,
          selectedId: _originId,
          excludeId: _destinationId,
          onChanged: (v) => setState(() => _originId = v),
        ),
        const SizedBox(height: 12),
        StopPickerField(
          label: 'Destino',
          icon: const Icon(Icons.location_on, color: Color(0xFF1D5FA7)),
          stops: _stops,
          selectedId: _destinationId,
          excludeId: _originId,
          onChanged: (v) => setState(() => _destinationId = v),
        ),
        const SizedBox(height: 12),
        _quantityCard(),
        if (_seatsRequired) ...[
          const SizedBox(height: 12),
          _emergencyFields(),
        ],
      ]),
    );
  }

  Widget _quantityCard() {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE4EBF3)),
      ),
      child: Row(children: [
        const Icon(Icons.confirmation_number_outlined, size: 20, color: Color(0xFF6B7A8F)),
        const SizedBox(width: 10),
        const Expanded(
          child: Text('Quantos bilhetes',
              style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
        ),
        IconButton(
          icon: const Icon(Icons.remove_circle_outline),
          onPressed: _quantity > 1
              ? () => setState(() {
                    _quantity--;
                    // Baixar a quantidade tem de largar os lugares a mais,
                    // senao ficavam escolhidos mais lugares do que bilhetes.
                    while (_pickedSeats.length > _quantity) {
                      _pickedSeats.removeLast();
                    }
                  })
              : null,
        ),
        Text('$_quantity',
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 20)),
        IconButton(
          icon: const Icon(Icons.add_circle_outline),
          onPressed: _quantity < 10 ? () => setState(() => _quantity++) : null,
        ),
      ]),
    );
  }

  /// Passo 3: a planta do autocarro sozinha no ecra.
  ///
  /// Antes abria-se num ecra empurrado por cima do formulario; agora e um
  /// passo do fluxo, com a mesma barra de progresso e o mesmo botao de
  /// avancar dos outros passos.
  Widget _stepSeats() {
    final map = _seatMap;
    if (map == null) {
      return const Center(child: Text('Sem planta de lugares para esta viagem.'));
    }
    return Column(children: [
      if (_error != null) _errorBanner(),
      Expanded(
        child: SeatMapView(
          seatMap: map,
          picked: _pickedSeats,
          onToggle: _toggleSeat,
        ),
      ),
      const SizedBox(height: 4),
      const SeatLegend(),
      const SizedBox(height: 8),
    ]);
  }

  void _toggleSeat(String label) {
    setState(() {
      if (_pickedSeats.contains(label)) {
        _pickedSeats.remove(label);
      } else if (_pickedSeats.length < _quantity) {
        _pickedSeats.add(label);
      } else if (_quantity == 1) {
        // Com um so lugar a vender, tocar noutro troca em vez de exigir
        // desmarcar primeiro.
        _pickedSeats
          ..clear()
          ..add(label);
      }
      HapticFeedback.selectionClick();
    });
  }

  Widget _stepPhoneAndConfirm() {
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _errorBanner(),
        Card(
          color: const Color(0xFFFFF8E1),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${_selectedTrip!['route_code']} - ${_selectedTrip!['route_name']}'),
              Text('${_fare!['origin']} → ${_fare!['destination']}'),
              if (_rates.isNotEmpty) ...[
                const SizedBox(height: 6),
                Row(children: [
                  const Text('Mostrar em', style: TextStyle(fontSize: 12)),
                  const SizedBox(width: 8),
                  for (final c in ['MZN', ..._rates.keys.toList()..sort()])
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text(c, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                        selected: _currency == c,
                        visualDensity: VisualDensity.compact,
                        onSelected: (_) => setState(() => _currency = c),
                      ),
                    ),
                ]),
              ],
              const Divider(),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                const Text('Preco unit.'),
                Text('${_fare!['fare_amount']} MZN', style: const TextStyle(fontWeight: FontWeight.bold)),
              ]),
              if (_rate != null)
                Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                  Text('Em $_currency (1 $_currency = ${_rate!.toStringAsFixed(2)} MZN)',
                      style: const TextStyle(fontSize: 12)),
                  Text(_inDisplay(_unitFare()),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                ]),
              // A quantidade e os lugares foram escolhidos nos passos
              // anteriores: aqui so se confirmam.
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                const Text('Quantidade'),
                Text('x$_quantity', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ]),
              if (_seatsRequired && _pickedSeats.isNotEmpty)
                Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                  const Text('Lugares'),
                  Text(_pickedSeats.join(', '),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                ]),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                const Text('TOTAL', style: TextStyle(fontWeight: FontWeight.bold)),
                // A moeda ESCOLHIDA aparece em grande; a outra na linha
                // pequena. A cobranca e sempre em MZN.
                Text(
                  _rate != null
                      ? _inDisplay(_unitFare() * _quantity)
                      : '${(double.parse(_fare!['fare_amount'].toString()) * _quantity).toStringAsFixed(2)} MZN',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: Color(0xFF1D5FA7)),
                ),
              ]),
              if (_rate != null)
                Align(
                  alignment: Alignment.centerRight,
                  child: Text(
                    '≈ ${(double.parse(_fare!['fare_amount'].toString()) * _quantity).toStringAsFixed(2)} MZN · cobranca em MZN',
                    style: const TextStyle(fontSize: 11.5),
                  ),
                ),
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
            // setState para a linha "indique o telefone..." por cima do botao
            // acompanhar o que esta a ser escrito.
            onChanged: (v) => setState(() => _phone = v),
          )
        else
          _cardCapturePanel(),
        // O botao de cobrar vive na barra fixa do fundo, sempre a vista.
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
            onPressed: () { _pollTimer?.cancel(); setState(() { _error = null; _step = _Step.payment; }); },
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
                  _kv('Tarifa unitaria', '${_unitFare().toStringAsFixed(2)} MZN', fg, muted),
                  _kv('Quantidade', 'x$_quantity', fg, muted),
                  const Divider(height: 14),
                  Row(children: [
                    Expanded(child: Text('TOTAL A COBRAR',
                        style: TextStyle(color: muted, fontSize: 11.5, letterSpacing: 1.0, fontWeight: FontWeight.w700))),
                    Text('${(_unitFare() * _quantity).toStringAsFixed(2)} MZN',
                        style: TextStyle(color: fg, fontSize: 20, fontWeight: FontWeight.w800)),
                  ]),
                  Text('Se o passageiro tiver pacote, o desconto e aplicado no pagamento.',
                      style: TextStyle(color: muted, fontSize: 10.5)),
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

  /// Contacto de emergência do passageiro, pedido só nas viagens longas.
  ///
  /// Vai para o manifesto de bordo. O balcão é o único momento em que há
  /// alguém a quem perguntar — depois do acidente já não serve.
  Widget _emergencyFields() {
    return Card(
      color: const Color(0xFFFFF6E8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: const [
            Icon(Icons.emergency_share_outlined, size: 18, color: Color(0xFFB07B24)),
            SizedBox(width: 8),
            Expanded(
              child: Text('Contacto de emergencia',
                  style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
            ),
          ]),
          const Text('Obrigatorio nesta rota. Vai no manifesto de bordo.',
              style: TextStyle(fontSize: 11.5, color: Color(0xFF6B7A8F))),
          const SizedBox(height: 10),
          TextField(
            controller: _emergNameCtrl,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'Nome',
              floatingLabelBehavior: FloatingLabelBehavior.always,
              hintText: 'Ex.: Maria Sitoe',
              prefixIcon: Icon(Icons.person_outline),
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _emergPhoneCtrl,
            keyboardType: TextInputType.phone,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(9),
            ],
            decoration: const InputDecoration(
              labelText: 'Telefone (9 digitos)',
              floatingLabelBehavior: FloatingLabelBehavior.always,
              hintText: '84/85/86/87...',
              prefixIcon: Icon(Icons.phone_outlined),
            ),
            onChanged: (_) => setState(() {}),
          ),
        ]),
      ),
    );
  }

  /// O que falta para poder cobrar, em palavras. Vazio quando nao falta nada.
  ///
  /// Um botao cinzento sem explicacao deixa o agente parado com o passageiro
  /// a frente, sem saber o que fazer.
  String _missingForSale() {
    if (!_seatsRequired) return '';
    if (_pickedSeats.length != _quantity) {
      final f = _quantity - _pickedSeats.length;
      return f > 0 ? 'Escolha mais $f lugar(es).' : 'Escolheu lugares a mais.';
    }
    if (_emergPhoneCtrl.text.trim().length != 9) {
      return 'Indique o contacto de emergencia (9 digitos).';
    }
    return '';
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

  double _unitFare() => double.tryParse('${_fare?['fare_amount'] ?? 0}') ?? 0;

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
              leading: const Icon(Icons.confirmation_number, color: Color(0xFF1D5FA7)),
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
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFF1D5FA7), minimumSize: const Size.fromHeight(50)),
          icon: const Icon(Icons.add),
          label: const Text('NOVA VENDA'),
          onPressed: _resetSale,
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
