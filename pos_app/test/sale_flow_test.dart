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
class _FakeApi extends AgentApi {
  _FakeApi({required this.seated}) : super(ApiClient(SecureStore()));

  final bool seated;

  @override
  Future<List<dynamic>> trips({int? routeId}) async => [
        {
          'id': 7,
          'route_code': 'R-XX',
          'route_name': 'Maputo - Xai-Xai',
          'vehicle': 'AAA-11-MC',
          'driver': 'Joao Sitoe',
          'status': 'scheduled',
        },
      ];

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
      'tickets': const [],
    };
  }

  @override
  Future<Map<String, dynamic>> paymentStatus(String reference) async =>
      {'status': 'confirmed', 'tickets': const []};
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

  testWidgets('rota com lugar marcado vende em quatro passos', (tester) async {
    await _pump(tester, _FakeApi(seated: true));
    await _ateTrajecto(tester);

    expect(find.text('PASSO 2 DE 4'), findsOneWidget);
    expect(find.text('Contacto de emergencia'), findsOneWidget);
    // Sem contacto de emergencia o servidor recusaria a venda: o botao diz-lo
    // antes, em vez de deixar o agente descobrir depois de cobrar.
    expect(find.text('Indique o contacto de emergencia (9 digitos).'),
        findsOneWidget);
    expect(_actionButton(tester).onPressed, isNull);

    await tester.enterText(find.byType(TextField).last, '849999999');
    await tester.pumpAndSettle();
    expect(_actionLabel(tester), 'ESCOLHER LUGARES');

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(find.text('PASSO 3 DE 4'), findsOneWidget);
    expect(find.text('1A'), findsOneWidget);
    expect(find.text('Escolha mais 1 lugar.'), findsOneWidget);
    expect(_actionButton(tester).onPressed, isNull);

    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    expect(_actionLabel(tester), 'AVANCAR COM 2C');

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    expect(find.text('PASSO 4 DE 4'), findsOneWidget);
    // O lugar tem de estar a vista no pagamento: veio de um ecra atras.
    expect(find.text('2C'), findsOneWidget);
  });

  testWidgets('a quantidade manda no numero de lugares a escolher',
      (tester) async {
    await _pump(tester, _FakeApi(seated: true));
    await _ateTrajecto(tester);
    await tester.enterText(find.byType(TextField).last, '849999999');
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
    await tester.enterText(find.byType(TextField).last, '849999999');
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
    await tester.enterText(find.byType(TextField).last, '849999999');
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

    // Venda 1, completa.
    await _ateTrajecto(tester);
    await tester.enterText(find.byType(TextField).last, '840000001');
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
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
    await tester.tap(find.text('1A'));
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

  testWidgets('recuar do pagamento volta aos lugares, nao ao inicio',
      (tester) async {
    await _pump(tester, _FakeApi(seated: true));
    await _ateTrajecto(tester);
    await tester.enterText(find.byType(TextField).last, '849999999');
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    expect(find.text('PASSO 4 DE 4'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    expect(find.text('PASSO 3 DE 4'), findsOneWidget);
    expect(_actionLabel(tester), 'AVANCAR COM 2C');

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    expect(find.text('PASSO 2 DE 4'), findsOneWidget);
    // O contacto de emergencia escrito nao se perde ao recuar.
    expect(find.text('849999999'), findsOneWidget);
  });
}
