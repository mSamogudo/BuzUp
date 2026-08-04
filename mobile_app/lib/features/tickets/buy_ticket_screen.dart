import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/bus_loader.dart';
import '../../core/documents.dart';
import '../../core/logger.dart';
import '../../core/providers.dart';
import '../../core/seat_map_screen.dart';
import '../../core/theme.dart';
import 'stop_picker.dart';

/// Como o passageiro paga o bilhete: com o saldo BusUp (fluxo original) ou
/// directamente com M-Pesa/e-Mola, sem ser obrigado a carregar a carteira.
enum _PayMethod { wallet, mobileMoney }

/// Os passos da compra.
///
/// Numa carreira urbana o passo do lugar nao existe: entra-se, valida-se e
/// senta-se onde houver. Ai a compra sao dois passos — viagem e pagamento —
/// como sempre foi.
enum _Step { search, seat, payment }

class BuyTicketScreen extends ConsumerStatefulWidget {
  const BuyTicketScreen({super.key});

  @override
  ConsumerState<BuyTicketScreen> createState() => _BuyTicketScreenState();
}

class _BuyTicketScreenState extends ConsumerState<BuyTicketScreen> {
  _Step _step = _Step.search;

  List<Map> _stops = const [];
  bool _loadingStops = true;
  String? _stopsError;

  Map<String, dynamic>? _quote;
  bool _quoting = false;
  bool _purchasing = false;
  String? _error;
  String? _waitingMessage;

  int? _originId;
  int? _destinationId;

  // A app nunca pergunta ao passageiro que tipo de viagem e: o orcamento
  // devolve `requires_seat_selection` a partir da rota que liga a origem ao
  // destino, e so entao aparecem a partida, a planta e o contacto de
  // emergencia. Numa carreira urbana estes passos nem existem.
  bool _seatsRequired = false;
  DateTime _travelDate = DateTime.now();
  List<Map<String, dynamic>> _departures = const [];
  bool _loadingDepartures = false;
  int? _tripId;
  Map<String, dynamic>? _seatMap;
  bool _loadingSeatMap = false;
  String? _seat;

  // Contacto de emergencia: pedido nas mesmas rotas que marcam lugar
  // (interprovincial/internacional), porque e para o manifesto de bordo que
  // serve. Numa carreira urbana nem aparece.
  final _emergencyNameCtrl = TextEditingController();
  final _emergencyPhoneCtrl = TextEditingController();
  final _searchScroll = ScrollController();
  String _holderName = '';
  String _holderDocType = '';
  String _holderDocNumber = '';

  // Documento de identificacao: exigido nas rotas interprovinciais e
  // internacionais, onde o bilhete e nominal e pode ser conferido na fronteira.
  // So se PERGUNTA quando a conta ainda nao tem um valido guardado — quem ja
  // registou o BI no perfil nao o volta a escrever a cada compra.
  List<DocumentRule> _docRules = kDocumentFallback;
  String _docType = 'bi';
  final _docNumberCtrl = TextEditingController();
  bool _usePackage = true;
  // Os pacotes especiais sao passes do dia-a-dia: so valem em carreiras
  // urbanas/interurbanas. Quem decide e o servidor (tipo de servico da rota);
  // aqui so se esconde o interruptor onde ele nao pode ser usado, para nao
  // prometer um desconto que a compra ia recusar.
  bool _allowsPackage = true;

  _PayMethod _method = _PayMethod.wallet;
  final _phoneCtrl = TextEditingController();

  // Moeda de exibicao (rand nas rotas p/ Africa do Sul). So visual: a
  // cobranca e sempre em meticais; a escolha fica gravada no bilhete.
  Map<String, double> _rates = const {};
  String _currency = 'MZN';

  @override
  void initState() {
    super.initState();
    ref.read(passengerApiProvider).publicTrips().then((d) {
      if (!mounted) return;
      setState(() {
        _stops = (d['stops'] as List?)?.cast<Map>() ?? const [];
        _loadingStops = false;
      });
    }).catchError((e) {
      if (!mounted) return;
      setState(() {
        _stopsError = e is DioException ? ApiClient.extractError(e) : '$e';
        _loadingStops = false;
      });
    });
    ref.read(passengerApiProvider).documentTypes().then((items) {
      if (!mounted || items.isEmpty) return;
      setState(() => _docRules = items.map(DocumentRule.fromJson).toList());
    }).catchError((_) {/* fica a lista de recurso: melhor comprar do que travar */});
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
      if (!mounted) return;
      if (_phoneCtrl.text.isEmpty && phone.isNotEmpty) {
        _phoneCtrl.text = phone.startsWith('258') ? phone.substring(3) : phone;
      }
      // O bilhete das rotas com lugar marcado e nominal e o servidor exige o
      // nome; guarda-se o do titular da conta para a compra directa o enviar.
      final p = (me['passenger'] as Map?) ?? me;
      setState(() {
        _holderName = (p['full_name'] ?? me['full_name'] ?? '').toString();
        _holderDocType = (p['document_type'] ?? '').toString();
        _holderDocNumber = (p['document_number'] ?? '').toString();
      });
    }).catchError((_) {});
  }

  @override
  void dispose() {
    _phoneCtrl.dispose();
    _emergencyNameCtrl.dispose();
    _emergencyPhoneCtrl.dispose();
    _docNumberCtrl.dispose();
    _searchScroll.dispose();
    super.dispose();
  }

  // --- passos ---------------------------------------------------------------

  /// Os passos desta compra, por ordem. Numa carreira urbana sao dois.
  List<String> get _stepLabels => _seatsRequired
      ? const ['Viagem', 'Lugar', 'Pagamento']
      : const ['Viagem', 'Pagamento'];

  int get _stepIndex => _seatsRequired
      ? _step.index
      : (_step == _Step.payment ? 1 : 0);

  void _goTo(_Step s) {
    FocusScope.of(context).unfocus();
    setState(() {
      _step = s;
      _error = null;
    });
  }

  /// Recuar um passo. Devolve false quando ja estamos no primeiro — ai quem
  /// chama fecha o ecra.
  bool _back() {
    switch (_step) {
      case _Step.search:
        return false;
      case _Step.seat:
        _goTo(_Step.search);
        return true;
      case _Step.payment:
        _goTo(_seatsRequired ? _Step.seat : _Step.search);
        return true;
    }
  }

  double? get _rate => _currency == 'MZN' ? null : _rates[_currency];

  String _fmtMzn(num n) =>
      '${n.toStringAsFixed(2).replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+\.)'), (m) => '${m[1]} ')} MZN';

  String _fmtDisplay(num mzn) {
    final r = _rate;
    if (r == null) return _fmtMzn(mzn);
    return '${(mzn / r).toStringAsFixed(2)} $_currency';
  }

  String _stopName(int? id) {
    for (final s in _stops) {
      if (s['id'] == id) return (s['name'] ?? '').toString();
    }
    return '';
  }

  // --- documento ------------------------------------------------------------

  /// A conta ja tem um documento que serve? Se sim, nao se pergunta nada.
  bool get _holderDocIsUsable {
    if (_holderDocNumber.trim().isEmpty) return false;
    return ruleFor(_docRules, _holderDocType).accepts(_holderDocNumber);
  }

  /// O tipo e o numero que vao com a compra: os da conta quando servem, os
  /// escritos agora quando nao.
  String get _effectiveDocType => _holderDocIsUsable ? _holderDocType : _docType;
  String get _effectiveDocNumber => _holderDocIsUsable
      ? normalizeDocument(_holderDocNumber)
      : normalizeDocument(_docNumberCtrl.text);

  /// O que esta errado no documento escrito, por palavras. Vazio quando esta
  /// bem — ou quando nao ha nada a perguntar.
  String _docProblem() {
    if (!_seatsRequired || _holderDocIsUsable) return '';
    final regra = ruleFor(_docRules, _docType);
    final numero = normalizeDocument(_docNumberCtrl.text);
    if (numero.isEmpty) return 'Indique o numero do documento.';
    if (!regra.accepts(numero)) {
      return regra.help.isEmpty ? '${regra.label}: numero invalido.' : regra.help;
    }
    return '';
  }

  Map<String, dynamic>? get _selectedDeparture {
    for (final t in _departures) {
      if (t['trip_id'] == _tripId) return t;
    }
    return null;
  }

  // --- dados ----------------------------------------------------------------

  Future<void> _onRouteChanged() async {
    // Trocar de par origem/destino invalida tudo o que dependia da rota
    // anterior: a partida, o lugar e ate o tipo de viagem.
    setState(() {
      _tripId = null;
      _seat = null;
      _seatMap = null;
      _departures = const [];
      _quote = null;
      _error = null;
    });
    await _refreshQuote(reloadDepartures: true);
  }

  /// Recalcula o preco.
  ///
  /// `reloadDepartures` so quando a ROTA muda: recarregar as partidas larga a
  /// viagem e o lugar escolhidos, e fazer isso a partir do passo do pagamento
  /// (onde o interruptor do pacote tambem recalcula) apagava em silencio o
  /// lugar que o passageiro tinha acabado de escolher.
  Future<void> _refreshQuote({bool reloadDepartures = false}) async {
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
            usePackage: _usePackage && _allowsPackage,
          );
      Log.info('ticket.quote ok', data: res);
      if (!mounted) return;
      final needsSeat = res['requires_seat_selection'] == true;
      var typeChanged = false;
      setState(() {
        _quote = res;
        _allowsPackage = res['allows_package_discounts'] != false;
        if (needsSeat != _seatsRequired) {
          _seatsRequired = needsSeat;
          _tripId = null;
          _seat = null;
          _seatMap = null;
          _departures = const [];
          typeChanged = true;
        }
      });
      if (_seatsRequired && (reloadDepartures || typeChanged)) {
        await _loadDepartures();
      }
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

  String get _dateLabel {
    const meses = [
      'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
      'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
    ];
    final hoje = DateTime.now();
    final ehHoje = _travelDate.year == hoje.year &&
        _travelDate.month == hoje.month &&
        _travelDate.day == hoje.day;
    final d = '${_travelDate.day} ${meses[_travelDate.month - 1]}';
    return ehHoje ? '$d (hoje)' : d;
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _travelDate,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 90)),
      helpText: 'Data da viagem',
    );
    if (picked == null) return;
    setState(() => _travelDate = picked);
    await _loadDepartures();
  }

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
      _loadingSeatMap = true;
    });
    try {
      final map = await ref.read(passengerApiProvider).tripSeats(tripId);
      if (!mounted) return;
      setState(() => _seatMap = map);
      _revealEmergencyCard();
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _error = ApiClient.extractError(e));
    } finally {
      if (mounted) setState(() => _loadingSeatMap = false);
    }
  }

  /// Rola ate ao contacto de emergencia depois de escolhida a partida.
  ///
  /// O cartao nasce por baixo da lista de partidas: com oito partidas fica
  /// fora do ecra, e o passageiro le "indique o telefone do contacto de
  /// emergencia" sem ver campo nenhum onde o escrever.
  void _revealEmergencyCard() {
    if (!_seatsRequired) return;
    if (_emergencyPhoneCtrl.text.trim().isNotEmpty) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_searchScroll.hasClients) return;
      _searchScroll.animateTo(
        _searchScroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeOutCubic,
      );
    });
  }

  // --- compra ---------------------------------------------------------------

  Future<void> _purchaseWithWallet() async {
    try {
      final res = await ref.read(passengerApiProvider).purchaseTicket(
            originStopId: _originId,
            destinationStopId: _destinationId,
            tripId: _tripId,
            seat: _seat,
            usePackage: _usePackage && _allowsPackage,
            displayCurrency: _currency,
            emergencyName: _emergencyNameCtrl.text.trim(),
            emergencyPhone: _emergencyPhoneCtrl.text.trim(),
            documentType: _effectiveDocType,
            documentNumber: _effectiveDocNumber,
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
    try {
      setState(() => _waitingMessage = 'A contactar a carteira movel...');
      final res = await ref.read(passengerApiProvider).directCheckout(
            originStopId: _originId!,
            destinationStopId: _destinationId!,
            originName: _stopName(_originId),
            destinationName: _stopName(_destinationId),
            payerPhone: phone,
            tripId: _tripId,
            seat: _seat,
            displayCurrency: _currency,
            emergencyName: _emergencyNameCtrl.text.trim(),
            emergencyPhone: _emergencyPhoneCtrl.text.trim(),
            passengerName: _holderName,
            documentType: _effectiveDocType,
            documentNumber: _effectiveDocNumber,
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

  // --- estrutura do ecra ----------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return PopScope(
      // O botao "recuar" do Android recua um passo em vez de abandonar a
      // compra: perder a partida e o lugar por carregar em recuar seria um
      // castigo por explorar.
      canPop: _step == _Step.search,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: Scaffold(
        backgroundColor: const Color(0xFFF2F5FA),
        // O passo do lugar nao tem campos de texto e precisa da altura toda
        // para calcular o tamanho do banco. Deixar o teclado (aberto no passo
        // anterior) encolher o ecra fazia a planta aparecer pequena e so
        // "crescer" quando o teclado fechava.
        resizeToAvoidBottomInset: _step != _Step.seat,
        appBar: AppBar(
          title: Text(_appBarTitle()),
          leading: IconButton(
            icon: Icon(_step == _Step.search ? Icons.close : Icons.arrow_back),
            onPressed: () {
              if (_back()) return;
              context.canPop() ? context.pop() : context.go('/tickets');
            },
          ),
        ),
        body: SafeArea(
          child: Column(children: [
            _stepHeader(),
            Expanded(child: _stepBody()),
            _bottomBar(),
          ]),
        ),
      ),
    );
  }

  String _appBarTitle() => switch (_step) {
        _Step.search => 'Comprar bilhete',
        _Step.seat => 'Escolha o seu lugar',
        _Step.payment => 'Pagamento',
      };

  /// Barra de progresso dos passos.
  ///
  /// Barra segmentada e nao circulos numerados com legenda: as legendas
  /// ("Pagamento") estouravam a linha num ecra de 320, e o que o passageiro
  /// precisa de saber e so onde esta e quanto falta.
  Widget _stepHeader() {
    final labels = _stepLabels;
    final current = _stepIndex;
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('PASSO ${current + 1} DE ${labels.length}',
              style: const TextStyle(
                  fontSize: 10.5, letterSpacing: 1.4,
                  fontWeight: FontWeight.w800, color: BuzUpColors.muted)),
          const Spacer(),
          Text(labels[current],
              style: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w900, color: BuzUpColors.navy)),
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
                  color: i <= current ? BuzUpColors.blue : const Color(0xFFDDE5EF),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ],
        ]),
      ]),
    );
  }

  Widget _stepBody() {
    if (_loadingStops) {
      return const Center(child: BusLoader(label: 'A carregar paragens...'));
    }
    if (_stopsError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text('Erro: $_stopsError',
              textAlign: TextAlign.center,
              style: const TextStyle(color: BuzUpColors.danger)),
        ),
      );
    }
    return switch (_step) {
      _Step.search => _searchStep(),
      _Step.seat => _seatStep(),
      _Step.payment => _paymentStep(),
    };
  }

  // --- passo 1: viagem ------------------------------------------------------

  Widget _searchStep() {
    return ListView(
      controller: _searchScroll,
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
      children: [
        StopPickerField(
          label: 'Origem',
          stops: _stops,
          selectedId: _originId,
          excludeId: _destinationId,
          onChanged: (v) {
            setState(() => _originId = v);
            _onRouteChanged();
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
            _onRouteChanged();
          },
        ),
        if (_quoting) ...[
          const SizedBox(height: 20),
          const Center(child: BusLoader(size: 120, label: 'A procurar viagens...')),
        ] else if (_quote != null && !_seatsRequired) ...[
          const SizedBox(height: 14),
          _urbanAvailableCard(),
        ] else if (_quote != null && _seatsRequired) ...[
          const SizedBox(height: 14),
          _dateRow(),
          const SizedBox(height: 10),
          _departuresBlock(),
          if (_tripId != null) ...[
            if (!_holderDocIsUsable) ...[
              const SizedBox(height: 14),
              _documentCard(),
            ],
            const SizedBox(height: 14),
            _emergencyCard(),
          ],
        ],
        if (_error != null) Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Text(_error!,
              style: const TextStyle(color: BuzUpColors.danger, fontSize: 12.5)),
        ),
      ],
    );
  }

  /// Carreira urbana: nao ha partida nem lugar a escolher. Confirma-se que a
  /// viagem existe e passa-se ao pagamento — como sempre foi.
  Widget _urbanAvailableCard() {
    final base = double.tryParse('${_quote!['base_fare'] ?? _quote!['fare_amount'] ?? 0}') ?? 0;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF7F1),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFBFE3C8)),
      ),
      child: Row(children: [
        const Icon(Icons.check_circle, color: Color(0xFF2A9D8F), size: 22),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Viagem disponivel',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900)),
            const SizedBox(height: 2),
            Text(
              'Carreira urbana: sem lugar marcado. Tarifa ${_fmtMzn(base)}.',
              style: const TextStyle(fontSize: 12, color: BuzUpColors.muted, height: 1.35),
            ),
          ]),
        ),
      ]),
    );
  }

  Widget _dateRow() {
    return Row(children: [
      const Icon(Icons.event, size: 18, color: BuzUpColors.muted),
      const SizedBox(width: 8),
      const Text('Data da viagem',
          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      const Spacer(),
      OutlinedButton.icon(
        icon: const Icon(Icons.calendar_today, size: 15),
        label: Text(_dateLabel, style: const TextStyle(fontWeight: FontWeight.w800)),
        style: OutlinedButton.styleFrom(
          visualDensity: VisualDensity.compact,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        onPressed: _pickDate,
      ),
    ]);
  }

  Widget _departuresBlock() {
    if (_loadingDepartures) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))),
      );
    }
    if (_departures.isEmpty) {
      // Sem partidas o passageiro fica sem saber o que fazer a seguir. A saida
      // — escolher outro dia — passa a ser um botao grande no meio do vazio, e
      // nao um link discreto no cabecalho.
      return Container(
        padding: const EdgeInsets.fromLTRB(18, 22, 18, 20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFE4EBF3)),
        ),
        child: Column(children: [
          const Icon(Icons.event_busy, size: 34, color: Color(0xFFB7C4D3)),
          const SizedBox(height: 10),
          Text('Sem partidas a venda em $_dateLabel',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text('Esta ligacao pode ter partidas noutros dias.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12.5, color: BuzUpColors.muted)),
          const SizedBox(height: 14),
          FilledButton.icon(
            icon: const Icon(Icons.calendar_month, size: 18),
            label: const Text('ESCOLHER OUTRA DATA',
                style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.4)),
            style: FilledButton.styleFrom(
              backgroundColor: BuzUpColors.blue,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: _pickDate,
          ),
        ]),
      );
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Padding(
        padding: const EdgeInsets.only(left: 2, bottom: 6),
        child: Text(
          '${_departures.length} partida${_departures.length == 1 ? '' : 's'} em $_dateLabel',
          style: const TextStyle(fontSize: 12, color: BuzUpColors.muted, fontWeight: FontWeight.w700),
        ),
      ),
      for (final t in _departures) _departureTile(t),
    ]);
  }

  Widget _departureTile(Map<String, dynamic> t) {
    final id = t['trip_id'] as int?;
    final selected = id != null && id == _tripId;
    final departure = (t['departure'] ?? '').toString();
    final hour = departure.length >= 16 ? departure.substring(11, 16) : '--:--';
    final seats = t['seats_available'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: selected ? BuzUpColors.blue.withValues(alpha: 0.06) : Colors.white,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: id == null ? null : () => _selectDeparture(id),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
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
                  Text(hour, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
                  Text(
                    '${t['route_name'] ?? t['route_code'] ?? ''}'
                    '${t['vehicle'] != null ? " · ${t['vehicle']}" : ""}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
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
      ),
    );
  }

  /// Documento de identificação, pedido só nas viagens longas — e só quando a
  /// conta ainda não tem um guardado.
  ///
  /// O bilhete destas rotas é nominal: entra no manifesto de bordo e pode ser
  /// conferido na fronteira. Numa carreira urbana não aparece.
  Widget _documentCard() {
    final regra = ruleFor(_docRules, _docType);
    final problema = _docProblem();
    // Só se avisa depois de escrever alguma coisa: acusar um campo ainda vazio
    // é ralhar antes da falta.
    final mostraErro = _docNumberCtrl.text.trim().isNotEmpty && problema.isNotEmpty;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE4EBF3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: const [
          Icon(Icons.badge_outlined, size: 18, color: BuzUpColors.blue),
          SizedBox(width: 8),
          Expanded(
            child: Text('Documento de identificacao',
                style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
          ),
        ]),
        const SizedBox(height: 2),
        const Text(
          'O bilhete desta viagem e nominal e pode ser conferido na fronteira.',
          style: TextStyle(fontSize: 11.5, color: BuzUpColors.muted, height: 1.35),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _docType,
          decoration: const InputDecoration(
            labelText: 'Tipo',
            floatingLabelBehavior: FloatingLabelBehavior.always,
            prefixIcon: Icon(Icons.description_outlined, size: 20),
          ),
          items: [
            for (final r in _docRules)
              DropdownMenuItem(value: r.value, child: Text(r.label)),
          ],
          // Trocar de tipo depois de escrever: o numero e refiltrado pela regra
          // nova, senao ficavam letras num campo que passou a ser so digitos.
          onChanged: (v) => setState(() {
            _docType = v ?? 'bi';
            _docNumberCtrl.text = ruleFor(_docRules, _docType)
                .filter(_docNumberCtrl.text);
          }),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _docNumberCtrl,
          // Sem `maxLength`: ele corta o texto CRU, antes de os espacos serem
          // tirados. Um BI escrito "1101 0012 3456 A" (17 caracteres) era
          // truncado a meio e ficava invalido sem o passageiro perceber
          // porque. O limite e aplicado depois de normalizar, em `filter`.
          keyboardType: regra.digitsOnly ? TextInputType.number : TextInputType.text,
          textCapitalization: TextCapitalization.characters,
          decoration: InputDecoration(
            labelText: 'Numero',
            floatingLabelBehavior: FloatingLabelBehavior.always,
            hintText: regra.placeholder,
            counterText: '',
            prefixIcon: const Icon(Icons.pin_outlined, size: 20),
            helperText: mostraErro ? null : regra.help,
            helperMaxLines: 2,
            errorText: mostraErro ? problema : null,
            errorMaxLines: 2,
          ),
          // Normaliza enquanto se escreve: o campo passa a recusar o que o
          // servidor recusaria, em vez de deixar chegar ao pagamento.
          onChanged: (v) {
            final limpo = regra.filter(v);
            if (limpo != v) {
              _docNumberCtrl.value = TextEditingValue(
                text: limpo,
                selection: TextSelection.collapsed(offset: limpo.length),
              );
            }
            setState(() {});
          },
        ),
      ]),
    );
  }

  /// Contacto de emergência, pedido só nas viagens longas.
  ///
  /// Numa viagem de horas, longe de casa, é o único modo de avisar a família
  /// se algo correr mal — e não serve de nada pedi-lo depois do acidente. Vai
  /// para o manifesto de bordo que o motorista leva.
  Widget _emergencyCard() {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE4EBF3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: const [
          Icon(Icons.emergency_share_outlined, size: 18, color: BuzUpColors.orange),
          SizedBox(width: 8),
          Expanded(
            child: Text('Contacto de emergencia',
                style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
          ),
        ]),
        const SizedBox(height: 2),
        const Text(
          'Quem avisamos se algo correr mal durante a viagem. Vai no manifesto de bordo.',
          style: TextStyle(fontSize: 11.5, color: BuzUpColors.muted, height: 1.35),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _emergencyNameCtrl,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(
            labelText: 'Nome',
            floatingLabelBehavior: FloatingLabelBehavior.always,
            hintText: 'Ex.: Maria Sitoe',
            prefixIcon: Icon(Icons.person_outline, size: 20),
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _emergencyPhoneCtrl,
          keyboardType: TextInputType.phone,
          decoration: const InputDecoration(
            labelText: 'Telefone',
            floatingLabelBehavior: FloatingLabelBehavior.always,
            hintText: '84/85/86/87...',
            prefixIcon: Icon(Icons.phone_outlined, size: 20),
          ),
          onChanged: (_) => setState(() {}),
        ),
      ]),
    );
  }

  // --- passo 2: lugar -------------------------------------------------------

  Widget _seatStep() {
    if (_loadingSeatMap || _seatMap == null) {
      return const Center(child: BusLoader(label: 'A carregar a planta...'));
    }
    return Column(children: [
      Expanded(
        child: SeatMapView(
          seatMap: _seatMap!,
          picked: _seat == null ? const [] : [_seat!],
          onToggle: (label) => setState(() => _seat = _seat == label ? null : label),
        ),
      ),
      const SizedBox(height: 4),
      const SeatLegend(),
      const SizedBox(height: 8),
    ]);
  }

  // --- passo 3: pagamento ---------------------------------------------------

  Widget _paymentStep() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
      children: [
        _tripSummaryCard(),
        const SizedBox(height: 14),
        const Text('Como quer pagar',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        _methodSelector(),
        if (_method == _PayMethod.wallet && _allowsPackage)
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            value: _usePackage,
            onChanged: (v) {
              setState(() => _usePackage = v);
              _refreshQuote();
            },
            title: const Text('Usar pacote especial se disponivel'),
            subtitle: const Text('Quando activo, desconta primeiro do saldo do pacote.',
                style: TextStyle(fontSize: 11.5, color: BuzUpColors.muted)),
          ),
        if (_method == _PayMethod.mobileMoney) ...[
          // 4px deixava o campo colado aos cartoes de metodo, como se
          // fizesse parte do cartao seleccionado.
          const SizedBox(height: 14),
          TextField(
            controller: _phoneCtrl,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Telemovel que paga (M-Pesa ou e-Mola)',
              hintText: '84xxxxxxx / 86xxxxxxx',
              helperText: 'Vai receber o pedido de PIN neste numero.',
            ),
            // Sem isto a linha "indique o numero..." por cima do botao so
            // desaparecia quando alguma outra coisa redesenhasse o ecra.
            onChanged: (_) => setState(() {}),
          ),
        ],
        const SizedBox(height: 12),
        if (_rates.isNotEmpty) _currencySelector(),
        const SizedBox(height: 10),
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
          padding: const EdgeInsets.only(top: 10),
          child: Text(_error!,
              style: const TextStyle(color: BuzUpColors.danger, fontSize: 12.5)),
        ),
      ],
    );
  }

  /// O que se esta a comprar, em duas linhas. No passo do pagamento a origem,
  /// a partida e o lugar ja foram escolhidos ha dois ecras — sem isto o
  /// passageiro paga sem ver o que esta a pagar.
  Widget _tripSummaryCard() {
    final dep = _selectedDeparture;
    final departure = (dep?['departure'] ?? '').toString();
    final hour = departure.length >= 16 ? departure.substring(11, 16) : '';
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE4EBF3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.trip_origin, size: 15, color: BuzUpColors.blue),
          const SizedBox(width: 8),
          Expanded(
            child: Text(_stopName(_originId),
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
          ),
        ]),
        const Padding(
          padding: EdgeInsets.only(left: 7),
          child: SizedBox(height: 14, child: VerticalDivider(width: 1, thickness: 1, color: Color(0xFFD5E0EC))),
        ),
        Row(children: [
          const Icon(Icons.place, size: 15, color: BuzUpColors.orange),
          const SizedBox(width: 8),
          Expanded(
            child: Text(_stopName(_destinationId),
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
          ),
        ]),
        if (_seatsRequired) ...[
          const Divider(height: 18, color: Color(0xFFEDF2F8)),
          Row(children: [
            _chip(Icons.event, _dateLabel),
            if (hour.isNotEmpty) ...[const SizedBox(width: 8), _chip(Icons.schedule, hour)],
            if (_seat != null) ...[const SizedBox(width: 8), _chip(Icons.event_seat, 'Lugar $_seat')],
          ]),
        ],
      ]),
    );
  }

  Widget _chip(IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFFF2F6FB),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 13, color: BuzUpColors.mutedDark),
        const SizedBox(width: 5),
        Text(label, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800)),
      ]),
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
    if (_quote == null) return const SizedBox.shrink();
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
          // A moeda ESCOLHIDA e a que aparece em grande; a outra fica na
          // linha pequena. O debito continua sempre em MZN.
          Text(rate != null ? _fmtDisplay(due) : _fmtMzn(due),
              style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900, letterSpacing: -0.3)),
        ]),
        if (rate != null) Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Align(
            alignment: Alignment.centerRight,
            child: Text('≈ ${_fmtMzn(due)} · o debito e sempre em MZN',
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

  // --- barra de accao -------------------------------------------------------

  /// O que falta para avancar deste passo, em palavras. Vazio = pode avancar.
  ///
  /// Um botao desactivado sem explicacao e um beco sem saida: o passageiro
  /// escolhe o lugar, volta ao formulario e o botao continua cinzento sem
  /// dizer que falta o contacto de emergencia.
  String _missingForStep() {
    switch (_step) {
      case _Step.search:
        if (_originId == null) return 'Escolha a origem.';
        if (_destinationId == null) return 'Escolha o destino.';
        if (_quoting) return 'A procurar viagens...';
        if (_quote == null) {
          // Dizer "nao ha ligacao" quando o que houve foi um timeout seria
          // mandar o passageiro procurar outro destino sem motivo.
          return _error == null
              ? 'Nao ha ligacao entre estas paragens.'
              : 'Nao foi possivel calcular esta viagem.';
        }
        if (!_seatsRequired) return '';
        if (_departures.isEmpty) return 'Escolha uma data com partidas.';
        if (_tripId == null) return 'Escolha a hora de partida.';
        final doc = _docProblem();
        if (doc.isNotEmpty) return doc;
        if (_emergencyPhoneCtrl.text.trim().isEmpty) {
          return 'Indique o telefone do contacto de emergencia.';
        }
        return '';
      case _Step.seat:
        if (_seat == null) return 'Toque num lugar livre para o escolher.';
        return '';
      case _Step.payment:
        if (_method == _PayMethod.mobileMoney &&
            _phoneCtrl.text.replaceAll(RegExp(r'\D'), '').length < 9) {
          return 'Indique o numero de telemovel que paga (9 digitos).';
        }
        return '';
    }
  }

  String _actionLabel() {
    switch (_step) {
      case _Step.search:
        return _seatsRequired ? 'ESCOLHER LUGAR' : 'CONTINUAR';
      case _Step.seat:
        return _seat == null ? 'ESCOLHA UM LUGAR' : 'AVANCAR COM O LUGAR $_seat';
      case _Step.payment:
        return _payButtonLabel();
    }
  }

  void _onAction() {
    switch (_step) {
      case _Step.search:
        _goTo(_seatsRequired ? _Step.seat : _Step.payment);
      case _Step.seat:
        _goTo(_Step.payment);
      case _Step.payment:
        _purchase();
    }
  }

  /// Barra fixa no fundo: a accao do passo esta SEMPRE visivel, sem rolar.
  Widget _bottomBar() {
    final missing = _missingForStep();
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Color(0xFFE4EBF3))),
      ),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        if (missing.isNotEmpty && !_purchasing)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(children: [
              const Icon(Icons.info_outline, size: 15, color: BuzUpColors.muted),
              const SizedBox(width: 6),
              Expanded(
                child: Text(missing,
                    style: const TextStyle(fontSize: 12, color: BuzUpColors.muted)),
              ),
            ]),
          ),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: BuzUpColors.blue,
              padding: const EdgeInsets.symmetric(vertical: 15),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: (_purchasing || missing.isNotEmpty) ? null : _onAction,
            child: _purchasing
                ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : Text(_actionLabel(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5)),
          ),
        ),
      ]),
    );
  }

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
