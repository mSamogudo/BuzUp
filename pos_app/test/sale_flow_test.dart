import 'package:pos_app/core/agent_api.dart';
import 'package:pos_app/core/api_client.dart';
import 'package:pos_app/core/providers.dart';
import 'package:pos_app/core/storage.dart';
import 'package:pos_app/features/sale/sale_flow_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// A venda ao balcao passou a ser um assistente: viagem → trajecto → lugares →
/// pagamento (e sem o passo dos lugares numa carreira urbana).
///
/// Estes testes fixam o que nao se ve num emulador de relance: que passos
/// existem para cada tipo de rota, que o botao de avancar esta sempre la e diz
/// o que falta, e que a quantidade escolhida manda no numero de lugares.
///
/// O agente tem o passageiro a frente e uma fila atras. Um botao cinzento sem
/// explicacao, ou um lugar a mais vendido por engano, custam-lhe a venda.

const _stops = [
  {'id': 1, 'name': 'Maputo Junta', 'code': 'JNT'},
  {'id': 2, 'name': 'Xai-Xai Terminal', 'code': 'XXT'},
];

const _seatMapRows = [
  {
    'row': 1,
    'left': [
      {'label': '1A', 'occupied': false},
    ],
    'right': [
      {'label': '1C', 'occupied': false},
      {'label': '1D', 'occupied': true},
    ],
  },
  {
    'row': 2,
    'left': [
      {'label': '2A', 'occupied': false},
    ],
    'right': [
      {'label': '2C', 'occupied': false},
      {'label': '2D', 'occupied': false},
    ],
  },
];

/// API falsa: nao ha rede nos testes. Herda de `AgentApi` para as assinaturas
/// ficarem presas as reais.
const _bilhetesEmitidos = [
  {
    'uuid': 'uuid-bilhete-1',
    'reference': 'S-1',
    'route_code': 'R-XX',
    'origin_stop': 'Maputo Junta',
    'destination_stop': 'Xai-Xai Terminal',
    'fare_amount': '250.00',
    'status': 'active',
  },
];

class _FakeApi extends AgentApi {
  _FakeApi({required this.seated}) : super(ApiClient(SecureStore()));

  final bool seated;

  /// O `date` com que a lista foi pedida da ultima vez. `null` e hoje.
  String? diaPedido;

  @override
  Future<List<dynamic>> trips({int? routeId, String? date}) async {
    diaPedido = date;
    return [
      {
        'id': 7,
        'route_code': 'R-XX',
        'route_name': 'Maputo - Xai-Xai',
        'vehicle': 'AAA-11-MC',
        'driver': 'Joao Sitoe',
        'status': 'scheduled',
        // A hora e o que distingue duas partidas da mesma rota no mesmo dia.
        'planned_departure_at':
            DateTime.now().add(const Duration(hours: 3)).toIso8601String(),
      },
    ];
  }

  @override
  Future<Map<String, dynamic>> trip(int tripId) async => {
        'stops': _stops,
        'seat_map': seated
            ? {'has_seat_map': true, 'rows': _seatMapRows}
            : {'has_seat_map': false, 'rows': const []},
      };

  @override
  Future<Map<String, dynamic>> quoteFare({
    required int tripId,
    required int originStopId,
    required int destinationStopId,
  }) async =>
      {
        'fare_amount': '750.00',
        'origin': 'Maputo Junta',
        'destination': 'Xai-Xai Terminal',
      };

  @override
  Future<Map<String, dynamic>> exchangeRates() async => const {'rates': {}};

  /// O que a venda enviou. Serve para provar que o contacto de emergência que
  /// chega ao servidor é o DESTA venda e não o da anterior.
  final vendas = <Map<String, dynamic>>[];

  /// Bilhetes validados a bordo, para o teste conferir o que foi pedido.
  final validados = <String>[];
  bool recusarValidacao = false;

  @override
  Future<Map<String, dynamic>> verifyTicketByUuid(String passUuid,
      {bool consume = true}) async {
    if (recusarValidacao) {
      return {'valid': false, 'reason': 'Bilhete ja utilizado.'};
    }
    validados.add(passUuid);
    return {'valid': true, 'consumed': consume};
  }

  @override
  Future<Map<String, dynamic>> createSale({
    required int tripId,
    required int originStopId,
    required int destinationStopId,
    String paymentMethod = 'mobile_money',
    String? passengerPhone,
    String? cardUid,
    String? qrToken,
    int quantity = 1,
    String? deviceSerial,
    bool autoRequestPayment = true,
    String? idempotencyKey,
    String displayCurrency = 'MZN',
    List<String> seats = const [],
    String emergencyName = '',
    String emergencyPhone = '',
    List<Map<String, String>> passengers = const [],
  }) async {
    vendas.add({
      'passengers': passengers,
      'seats': seats,
      'emergency_name': emergencyName,
      'emergency_phone': emergencyPhone,
      'quantity': quantity,
      'currency': displayCurrency,
      'phone': passengerPhone,
    });
    return {
      'sale_reference': 'S-1',
      'payment': {'reference': 'P-1', 'status': 'confirmed'},
      'tickets': _bilhetesEmitidos,
    };
  }

  @override
  Future<Map<String, dynamic>> paymentStatus(String reference) async =>
      {'status': 'confirmed', 'tickets': _bilhetesEmitidos};
}

/// O armazenamento seguro assenta em canais de plataforma que não existem num
/// teste. Só o número de série do aparelho é lido no fluxo de venda.
class _FakeStore extends SecureStore {
  @override
  Future<String?> getDeviceSerial() async => 'POS-TESTE-1';
}

Future<void> _pump(WidgetTester tester, _FakeApi api) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        agentApiProvider.overrideWithValue(api),
        secureStoreProvider.overrideWithValue(_FakeStore()),
      ],
      child: const MaterialApp(home: SaleFlowScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

/// Escolhe a viagem e depois origem e destino, como o agente.
Future<void> _ateTrajecto(WidgetTester tester) async {
  await tester.tap(find.text('R-XX - Maputo - Xai-Xai'));
  await tester.pumpAndSettle();

  await tester.tap(find.text('Origem'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Maputo Junta').last);
  await tester.pumpAndSettle();

  await tester.tap(find.text('Destino'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Xai-Xai Terminal').last);
  await tester.pumpAndSettle();
}

/// Vende ate ao ecra de sucesso, numa carreira urbana (sem lugares).
Future<void> _venderAteAoFim(WidgetTester tester) async {
  await _ateTrajecto(tester);
  await tester.tap(find.byType(FilledButton).last);
  await tester.pumpAndSettle();
  await tester.enterText(find.byType(TextField).last, '841234567');
  await tester.pumpAndSettle();
  await tester.tap(find.byType(FilledButton).last);
  // `pumpAndSettle` nao serve aqui: o ecra de espera do pagamento tem um
  // indicador que roda para sempre e nunca "assenta". Avanca-se por frames.
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 120));
  }
}

String _actionLabel(WidgetTester tester) {
  final btn = find.descendant(
    of: find.byType(FilledButton),
    matching: find.byType(Text),
  );
  return (tester.widget<Text>(btn.last)).data ?? '';
}

FilledButton _actionButton(WidgetTester tester) =>
    tester.widget<FilledButton>(find.byType(FilledButton).last);

void main() {
  // --- venda antecipada (reposta em 2026-09-03) -------------------------
  //
  // O agente de recepcao nao viaja: reserva para amanha e para a semana. Mas a
  // janela aberta de sete dias que houve em Agosto trazia a mesma rota
  // repetida dia apos dia, escrita igual, e bastava um toque distraido para o
  // bilhete sair para o autocarro errado. Daí a regra: a lista abre SEMPRE em
  // hoje, e o outro dia pede-se.

  testWidgets('a lista abre em hoje — nao pede dia nenhum ao servidor',
      (tester) async {
    final api = _FakeApi(seated: false);
    await _pump(tester, api);
    expect(api.diaPedido, isNull);
  });

  testWidgets('escolher outro dia pede esse dia ao servidor', (tester) async {
    final api = _FakeApi(seated: false);
    await _pump(tester, api);

    await tester.tap(find.text('Outro dia'));
    await tester.pumpAndSettle();
    // O calendario abre em hoje; o dia seguinte esta sempre visivel na grelha.
    final amanha = DateTime.now().add(const Duration(days: 1));
    await tester.tap(find.text('${amanha.day}').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ver partidas'));
    await tester.pumpAndSettle();

    final esperado = '${amanha.year.toString().padLeft(4, '0')}-'
        '${amanha.month.toString().padLeft(2, '0')}-'
        '${amanha.day.toString().padLeft(2, '0')}';
    expect(api.diaPedido, esperado);
  });

  testWidgets('vender para outro dia avisa no ecra que nao e hoje',
      (tester) async {
    final api = _FakeApi(seated: false);
    await _pump(tester, api);
    await tester.tap(find.text('Outro dia'));
    await tester.pumpAndSettle();
    final amanha = DateTime.now().add(const Duration(days: 1));
    await tester.tap(find.text('${amanha.day}').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ver partidas'));
    await tester.pumpAndSettle();

    // Sem este aviso, uma lista de partidas de amanha e visualmente igual a de
    // hoje — que e exactamente o engano que se quer evitar.
    expect(find.textContaining('Venda antecipada'), findsOneWidget);
    expect(find.text('Voltar a hoje'), findsOneWidget);
  });

  testWidgets('a hora da partida aparece na lista', (tester) async {
    // Mostrava rota, sentido, viatura e motorista — nunca a hora. Numa rota
    // com tres partidas no mesmo dia as linhas eram indistinguiveis.
    final api = _FakeApi(seated: false);
    await _pump(tester, api);
    final parte = DateTime.now().add(const Duration(hours: 3));
    final hhmm = '${parte.hour.toString().padLeft(2, '0')}:'
        '${parte.minute.toString().padLeft(2, '0')}';
    expect(find.textContaining(hhmm), findsOneWidget);
  });

  testWidgets('carreira urbana vende em tres passos', (tester) async {
    await _pump(tester, _FakeApi(seated: false));
    expect(find.text('PASSO 1 DE 3'), findsOneWidget);

    await _ateTrajecto(tester);
    expect(find.text('PASSO 2 DE 3'), findsOneWidget);
    // Sem lugar marcado nao ha contacto de emergencia a pedir.
    expect(find.text('Contacto de emergencia'), findsNothing);
    expect(_actionLabel(tester), 'CONTINUAR');

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(find.text('PASSO 3 DE 3'), findsOneWidget);
    expect(find.text('SOLICITAR PAGAMENTO'), findsOneWidget);

    // Sem telefone o botao esta fechado E diz porque.
    expect(find.text('Indique o telefone do passageiro (9 digitos).'),
        findsOneWidget);
    expect(_actionButton(tester).onPressed, isNull);

    await tester.enterText(find.byType(TextField).last, '841234567');
    await tester.pumpAndSettle();
    expect(_actionButton(tester).onPressed, isNotNull);
  });

  testWidgets('rota com lugar marcado vende em cinco passos', (tester) async {
    // Viagem -> trajecto -> lugares -> PASSAGEIROS -> pagamento.
    //
    // O passo dos passageiros nasceu quando o contacto de emergencia saiu do
    // trajecto: pedir a quem viaja o nome, o documento e o contacto de
    // emergencia sao a MESMA conversa com o passageiro, e estavam partidas
    // entre dois ecras com a escolha dos lugares pelo meio.
    await _pump(tester, _FakeApi(seated: true));
    await _ateTrajecto(tester);

    expect(find.text('PASSO 2 DE 5'), findsOneWidget);
    // O trajecto trata do PERCURSO. O contacto de emergencia ja nao vive aqui.
    expect(find.text('Contacto de emergencia'), findsNothing);
    expect(_actionLabel(tester), 'ESCOLHER LUGARES');

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(find.text('PASSO 3 DE 5'), findsOneWidget);
    expect(find.text('1A'), findsOneWidget);
    expect(find.text('Escolha mais 1 lugar.'), findsOneWidget);
    expect(_actionButton(tester).onPressed, isNull);

    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    expect(_actionLabel(tester), 'AVANCAR COM 2C');

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    // Agora sim: tudo o que ha para perguntar ao passageiro, junto.
    expect(find.text('PASSO 4 DE 5'), findsOneWidget);
    expect(find.text('Contacto de emergencia'), findsOneWidget);
    expect(find.text('Indique o contacto de emergencia (9 digitos).'),
        findsOneWidget);
    expect(_actionButton(tester).onPressed, isNull);

    await tester.enterText(find.byType(TextField).last, '849999999');
    await tester.pumpAndSettle();
    expect(_actionButton(tester).onPressed, isNotNull);

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    expect(find.text('PASSO 5 DE 5'), findsOneWidget);
    // O lugar tem de estar a vista no pagamento: veio de dois ecras atras.
    expect(find.text('2C'), findsOneWidget);
  });

  testWidgets('a quantidade manda no numero de lugares a escolher',
      (tester) async {
    await _pump(tester, _FakeApi(seated: true));
    await _ateTrajecto(tester);
    // O contacto de emergencia deixou de viver no trajecto: pergunta-se no
    // passo dos passageiros, junto com o nome e o documento.
    await tester.pumpAndSettle();

    // Tres bilhetes: tres lugares.
    await tester.tap(find.byIcon(Icons.add_circle_outline));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.add_circle_outline));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    expect(find.text('Escolha mais 3 lugares.'), findsOneWidget);

    for (final s in ['1A', '2A', '2C']) {
      await tester.tap(find.text(s));
      await tester.pumpAndSettle();
    }
    expect(_actionLabel(tester), 'AVANCAR COM 1A, 2A, 2C');
    expect(_actionButton(tester).onPressed, isNotNull);
  });

  testWidgets('baixar a quantidade larga os lugares a mais', (tester) async {
    await _pump(tester, _FakeApi(seated: true));
    await _ateTrajecto(tester);
    // O contacto de emergencia deixou de viver no trajecto: pergunta-se no
    // passo dos passageiros, junto com o nome e o documento.
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.add_circle_outline));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('1A'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    expect(_actionLabel(tester), 'AVANCAR COM 1A, 2C');

    // Recuar e vender so um bilhete: o segundo lugar tem de cair, senao
    // seguiam dois lugares para um bilhete so.
    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.remove_circle_outline));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    expect(_actionLabel(tester), 'AVANCAR COM 1A');
  });

  testWidgets('lugar ocupado nao pode ser vendido', (tester) async {
    await _pump(tester, _FakeApi(seated: true));
    await _ateTrajecto(tester);
    // O contacto de emergencia deixou de viver no trajecto: pergunta-se no
    // passo dos passageiros, junto com o nome e o documento.
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    // Um lugar ocupado desenha um X em vez da etiqueta.
    expect(find.text('1D'), findsNothing);
    await tester.tap(find.byIcon(Icons.close).first, warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(find.text('Escolha mais 1 lugar.'), findsOneWidget);
  });

  testWidgets('nova venda nao herda nada da venda anterior', (tester) async {
    final api = _FakeApi(seated: true);
    await _pump(tester, api);

    // Venda 1, completa: trajecto -> lugares -> passageiros -> pagamento.
    await _ateTrajecto(tester);
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    // Passo dos passageiros: o contacto de emergencia vive aqui.
    await tester.enterText(find.byType(TextField).last, '840000001');
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    // Pagamento.
    await tester.enterText(find.byType(TextField).last, '841111111');
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(api.vendas, hasLength(1));
    expect(api.vendas.first['emergency_phone'], '840000001');
    expect(api.vendas.first['seats'], ['2C']);

    // NOVA VENDA: o passageiro seguinte e outra pessoa. Se o contacto de
    // emergencia ficasse no ecra, o familiar do passageiro anterior seguia no
    // manifesto de bordo do seguinte — e ninguem daria por isso.
    await tester.tap(find.text('NOVA VENDA'));
    await tester.pumpAndSettle();

    // De volta ao inicio. A barra mostra 3 passos porque ainda nao se sabe se
    // a rota marca lugar — so se sabe depois de escolhida a viagem.
    expect(find.text('PASSO 1 DE 3'), findsOneWidget);
    await _ateTrajecto(tester);
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('1A'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    // Passo dos passageiros da venda 2: tem de estar VAZIO.
    expect(find.text('840000001'), findsNothing,
        reason: 'o contacto de emergencia da venda anterior ficou no ecra');
    expect(find.text('Indique o contacto de emergencia (9 digitos).'),
        findsOneWidget);
    expect(_actionButton(tester).onPressed, isNull);

    // E o que chega ao servidor na venda 2 e o contacto DESTA venda.
    await tester.enterText(find.byType(TextField).last, '840000002');
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, '842222222');
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(api.vendas, hasLength(2));
    expect(api.vendas.last['emergency_phone'], '840000002');
    expect(api.vendas.last['seats'], ['1A']);
    expect(api.vendas.last['quantity'], 1);
    expect(api.vendas.last['currency'], 'MZN');
  });

  testWidgets('o ecra de pagamento desenha-se sem erros de layout', (tester) async {
    // O defeito que este teste fixa: dois widgets do ecra de pagamento pediam
    // ALTURA INFINITA — um `Row` com `CrossAxisAlignment.stretch` e um scroll
    // horizontal — ambos dentro do scroll vertical do passo, onde nao ha
    // altura para esticar.
    //
    // Em debug isso lanca `BoxConstraints forces an infinite height`. Em
    // RELEASE nao estoira: desenha torto. E com o layout torto o hit-test
    // aterra no sitio errado — o campo do telefone ficava por dispor
    // (`RenderEditable NEEDS-LAYOUT`) e o agente escrevia sem que nada
    // acontecesse.
    //
    // Passei tres rondas a corrigir sintomas (Expanded, controlador, tema)
    // porque olhei sempre para o codigo e nunca corri isto. O teste ja existia
    // e nem sequer compilava.
    await _pump(tester, _FakeApi(seated: false));
    await _ateTrajecto(tester);
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(find.text('SOLICITAR PAGAMENTO'), findsOneWidget);
    // `pumpAndSettle` sem excepcoes ja prova que o layout fechou; isto garante
    // que o campo existe MESMO e recebe texto.
    await tester.enterText(find.byType(TextField).last, '849876543');
    await tester.pumpAndSettle();
    expect(find.text('849876543'), findsOneWidget);
    expect(_actionButton(tester).onPressed, isNotNull);
  });

  testWidgets('o campo do telefone aceita escrita tambem a numerario',
      (tester) async {
    await _pump(tester, _FakeApi(seated: false));
    await _ateTrajecto(tester);
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Numerário'));
    await tester.pumpAndSettle();
    expect(find.text('RECEBI O DINHEIRO'), findsOneWidget);

    await tester.enterText(find.byType(TextField).last, '841112223');
    await tester.pumpAndSettle();
    expect(find.text('841112223'), findsOneWidget);
    expect(_actionButton(tester).onPressed, isNotNull);
  });

  testWidgets('o pagamento oferece so M-Pesa/e-Mola e numerario', (tester) async {
    // O cartao NFC esta escondido a pedido do operador: a TPM-TUR ainda nao
    // usa cartoes, e um metodo que ninguem pode concluir e um toque em falso.
    // Se um dia voltar, e este teste que muda — de proposito, para que a
    // decisao seja tomada e nao acontecer por descuido.
    await _pump(tester, _FakeApi(seated: false));
    await _ateTrajecto(tester);
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(find.text('M-Pesa / e-Mola'), findsOneWidget);
    expect(find.text('Numerário'), findsOneWidget);
    expect(find.text('Cartão NFC'), findsNothing);
  });

  testWidgets('o bilhete pode ser validado ali mesmo, sem ler o QR',
      (tester) async {
    // Muitos bilhetes sao comprados JA DENTRO do autocarro. Nesses casos,
    // mandar o agente sair da venda, abrir o leitor e apontar ao telemovel do
    // passageiro — que ainda nem recebeu o SMS — e um passo sem ganho: ele
    // acabou de emitir o bilhete e sabe qual e.
    final api = _FakeApi(seated: false);
    await _pump(tester, api);
    await _venderAteAoFim(tester);

    expect(find.text('VENDA CONFIRMADA'), findsOneWidget);
    expect(find.text('VALIDAR A BORDO'), findsOneWidget);

    await tester.tap(find.text('VALIDAR A BORDO'));
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }

    expect(api.validados, ['uuid-bilhete-1']);
    expect(find.text('Validado — passageiro a bordo'), findsOneWidget);
    // Ja nao ha nada para tocar: nao se valida duas vezes.
    expect(find.text('VALIDAR A BORDO'), findsNothing);
  });

  testWidgets('validar continua a ser uma escolha, nao automatico',
      (tester) async {
    // Um bilhete vendido ao balcao para daqui a duas horas nao pode entrar no
    // manifesto como se ja tivesse embarcado.
    final api = _FakeApi(seated: false);
    await _pump(tester, api);
    await _venderAteAoFim(tester);

    expect(api.validados, isEmpty, reason: 'validou sem ninguem pedir');
    expect(find.text('VALIDAR A BORDO'), findsOneWidget);
  });

  testWidgets('uma validacao recusada diz porque e nao marca a bordo',
      (tester) async {
    final api = _FakeApi(seated: false)..recusarValidacao = true;
    await _pump(tester, api);
    await _venderAteAoFim(tester);

    await tester.tap(find.text('VALIDAR A BORDO'));
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }

    expect(find.text('Validado — passageiro a bordo'), findsNothing);
    expect(find.textContaining('ja utilizado'), findsOneWidget);
  });

  testWidgets('recuar do pagamento volta aos lugares, nao ao inicio',
      (tester) async {
    await _pump(tester, _FakeApi(seated: true));
    await _ateTrajecto(tester);
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    // Passo dos passageiros.
    expect(find.text('PASSO 4 DE 5'), findsOneWidget);
    await tester.enterText(find.byType(TextField).last, '849999999');
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    expect(find.text('PASSO 5 DE 5'), findsOneWidget);

    // Recuar devolve ao passo anterior, um de cada vez — e nao ao inicio.
    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    expect(find.text('PASSO 4 DE 5'), findsOneWidget);
    // O que foi escrito nao se perde ao recuar.
    expect(find.text('849999999'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    expect(find.text('PASSO 3 DE 5'), findsOneWidget);
    expect(_actionLabel(tester), 'AVANCAR COM 2C');
  });
}
