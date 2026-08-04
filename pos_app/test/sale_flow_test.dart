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
}

Future<void> _pump(WidgetTester tester, _FakeApi api) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [agentApiProvider.overrideWithValue(api)],
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
