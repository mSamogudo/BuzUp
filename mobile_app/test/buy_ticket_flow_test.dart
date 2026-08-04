import 'package:buzup_mobile/core/api_client.dart';
import 'package:buzup_mobile/core/passenger_api.dart';
import 'package:buzup_mobile/core/providers.dart';
import 'package:buzup_mobile/core/storage.dart';
import 'package:buzup_mobile/features/tickets/buy_ticket_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// A compra passou a ser um assistente: viagem → lugar → pagamento (e apenas
/// viagem → pagamento numa carreira urbana). Estes testes fixam as regras que
/// nao se veem a olho num emulador: que passos existem para cada tipo de rota,
/// que o botao de avancar aparece SEMPRE e diz o que falta, e que recuar nao
/// deita fora o que ja foi escolhido.
///
/// Foram escritos porque a versao anterior deste ecra chegou ao telemovel do
/// cliente com o botao de avancar inalcancavel — um defeito que um teste
/// destes apanha em dois segundos.

const _stops = [
  {'id': 1, 'name': 'Maputo Junta', 'code': 'JNT'},
  {'id': 2, 'name': 'Xai-Xai Terminal', 'code': 'XXT'},
];

const _seatMap = {
  'rows': [
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
  ],
};

/// API falsa: nao ha rede nos testes. Herda de `PassengerApi` para as
/// assinaturas ficarem presas as reais — se um metodo mudar, isto deixa de
/// compilar em vez de passar a testar uma coisa que ja nao existe.
class _FakeApi extends PassengerApi {
  _FakeApi({
    required this.seated,
    this.departures = const [],
    this.holderDocument = '',
  }) : super(ApiClient(SecureStore()));

  final bool seated;
  final List<Map<String, dynamic>> departures;

  /// BI já guardado na conta. Vazio = conta sem documento, que é quando a
  /// compra o tem de perguntar.
  final String holderDocument;

  @override
  Future<Map<String, dynamic>> publicTrips({int? routeId}) async =>
      {'stops': _stops};

  @override
  Future<Map<String, dynamic>> exchangeRates() async => const {'rates': {}};

  /// As regras a sério, como o servidor as devolve: os testes exercitam a
  /// validação verdadeira do BI, não uma versão amaciada.
  @override
  Future<List<Map<String, dynamic>>> documentTypes() async => [
        {
          'value': 'bi', 'label': 'Bilhete de Identidade',
          'pattern': r'^\d{12}[A-Z]$', 'max_length': 13,
          'placeholder': '110100123456A',
          'help': '13 caracteres: 12 digitos seguidos de uma letra.',
          'digits_only': false,
        },
        {
          'value': 'passport', 'label': 'Passaporte',
          'pattern': r'^[A-Z0-9]{6,9}$', 'max_length': 9,
          'placeholder': 'AB1234567',
          'help': '6 a 9 caracteres, so letras e numeros.',
          'digits_only': false,
        },
      ];

  @override
  Future<Map<String, dynamic>> me() async => {
        'phone': '258841234567',
        'passenger': {
          'full_name': 'Ana Cossa',
          if (holderDocument.isNotEmpty) 'document_type': 'bi',
          if (holderDocument.isNotEmpty) 'document_number': holderDocument,
        },
      };

  @override
  Future<Map<String, dynamic>> quoteTicket({
    int? routeId,
    int? originStopId,
    int? destinationStopId,
    int? tripId,
    int? passengerPackageId,
    bool usePackage = true,
  }) async =>
      {
        'base_fare': '750.00',
        'wallet_amount': '750.00',
        'requires_seat_selection': seated,
      };

  @override
  Future<List<Map<String, dynamic>>> searchDepartures({
    required int originStopId,
    required int destinationStopId,
    required String date,
  }) async =>
      departures;

  @override
  Future<Map<String, dynamic>> tripSeats(int tripId) async =>
      Map<String, dynamic>.from(_seatMap);
}

final _departuresOk = <Map<String, dynamic>>[
  {
    'trip_id': 77,
    'departure': '2026-08-05T06:30:00',
    'route_name': 'Maputo - Xai-Xai',
    'vehicle': 'AAA-11-MC',
    'seats_available': 21,
    'on_sale': true,
  },
];

Future<void> _pump(WidgetTester tester, _FakeApi api) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [passengerApiProvider.overrideWithValue(api)],
      child: const MaterialApp(home: BuyTicketScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

/// Escolhe origem e destino atraves da folha de pesquisa, como o passageiro.
Future<void> _chooseRoute(WidgetTester tester) async {
  await tester.tap(find.text('Origem'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Maputo Junta').last);
  await tester.pumpAndSettle();

  await tester.tap(find.text('Destino'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Xai-Xai Terminal').last);
  await tester.pumpAndSettle();
}

/// Preenche o que a viagem longa exige antes de escolher o lugar: documento
/// (quando a conta nao o tem) e contacto de emergencia.
Future<void> _preencherDadosDaViagem(WidgetTester tester,
    {bool comDocumento = true}) async {
  if (comDocumento) {
    await tester.enterText(find.byType(TextField).first, '110100123456A');
    await tester.pumpAndSettle();
  }
  await tester.enterText(find.byType(TextField).last, '849999999');
  await tester.pumpAndSettle();
}

FilledButton _actionButton(WidgetTester tester) =>
    tester.widget<FilledButton>(find.byType(FilledButton).last);

/// O rotulo do botao de accao, seja qual for o passo.
String _actionLabel(WidgetTester tester) {
  final btn = find.descendant(
    of: find.byType(FilledButton),
    matching: find.byType(Text),
  );
  return (tester.widget<Text>(btn.last)).data ?? '';
}

void main() {
  testWidgets('carreira urbana tem dois passos e vai direita ao pagamento',
      (tester) async {
    await _pump(tester, _FakeApi(seated: false));

    expect(find.text('PASSO 1 DE 2'), findsOneWidget);
    await _chooseRoute(tester);

    // Sem lugar marcado nao ha data nem partidas a escolher: basta a viagem
    // existir.
    expect(find.text('Viagem disponivel'), findsOneWidget);
    expect(find.text('PASSO 1 DE 2'), findsOneWidget);
    expect(_actionLabel(tester), 'CONTINUAR');

    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();

    expect(find.text('PASSO 2 DE 2'), findsOneWidget);
    expect(find.text('Como quer pagar'), findsOneWidget);
    expect(find.text('RESUMO DA COMPRA'), findsOneWidget);
  });

  testWidgets('pagar por M-Pesa sem numero diz o que falta', (tester) async {
    await _pump(tester, _FakeApi(seated: false));
    await _chooseRoute(tester);
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();

    await tester.tap(find.text('M-Pesa / e-Mola'));
    await tester.pumpAndSettle();
    // O numero da conta ja vem preenchido; apagado, o botao tem de dizer
    // porque fechou em vez de so ficar cinzento.
    await tester.enterText(find.byType(TextField).last, '');
    await tester.pumpAndSettle();
    expect(find.text('Indique o numero de telemovel que paga (9 digitos).'),
        findsOneWidget);
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull);

    await tester.enterText(find.byType(TextField).last, '841234567');
    await tester.pumpAndSettle();
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNotNull);
  });

  testWidgets('rota com lugar marcado tem tres passos', (tester) async {
    await _pump(tester, _FakeApi(seated: true, departures: _departuresOk));
    await _chooseRoute(tester);

    expect(find.text('PASSO 1 DE 3'), findsOneWidget);
    expect(find.text('06:30'), findsOneWidget);
    // O contacto de emergencia so aparece depois de escolhida a partida: pedi-lo
    // antes seria pedir dados para uma viagem que ainda nao existe.
    expect(find.text('Contacto de emergencia'), findsNothing);
  });

  testWidgets('sem partidas oferece escolher outra data', (tester) async {
    await _pump(tester, _FakeApi(seated: true, departures: const []));
    await _chooseRoute(tester);

    expect(find.textContaining('Sem partidas a venda'), findsOneWidget);
    expect(find.text('ESCOLHER OUTRA DATA'), findsOneWidget);
  });

  testWidgets('o botao diz o que falta em vez de ficar cinzento e calado',
      (tester) async {
    await _pump(tester, _FakeApi(seated: true, departures: _departuresOk));

    expect(find.text('Escolha a origem.'), findsOneWidget);
    await _chooseRoute(tester);
    expect(find.text('Escolha a hora de partida.'), findsOneWidget);

    await tester.tap(find.text('06:30'));
    await tester.pumpAndSettle();

    // O que falta aparece por ordem, um de cada vez — nao uma lista de
    // reclamacoes de uma vez so.
    expect(find.text('Indique o numero do documento.'), findsOneWidget);

    // Um BI com a forma errada e recusado ANTES do pagamento, com a regra por
    // palavras em vez de um "invalido" seco.
    await tester.enterText(find.byType(TextField).first, '12345');
    await tester.pumpAndSettle();
    expect(find.text('13 caracteres: 12 digitos seguidos de uma letra.'),
        findsWidgets);
    expect(_actionButton(tester).onPressed, isNull);

    await tester.enterText(find.byType(TextField).first, '110100123456A');
    await tester.pumpAndSettle();
    expect(find.text('Indique o telefone do contacto de emergencia.'),
        findsOneWidget);

    await tester.enterText(find.byType(TextField).last, '849999999');
    await tester.pumpAndSettle();
    expect(find.text('Indique o telefone do contacto de emergencia.'),
        findsNothing);
    expect(_actionLabel(tester), 'ESCOLHER LUGAR');
  });

  testWidgets('conta que ja tem BI nao volta a pedir o documento',
      (tester) async {
    await _pump(tester, _FakeApi(
      seated: true, departures: _departuresOk, holderDocument: '110100123456A'));
    await _chooseRoute(tester);
    await tester.tap(find.text('06:30'));
    await tester.pumpAndSettle();

    // Quem ja registou o documento no perfil nao o escreve a cada compra.
    expect(find.text('Documento de identificacao'), findsNothing);
    expect(find.text('Indique o numero do documento.'), findsNothing);

    await tester.enterText(find.byType(TextField).last, '849999999');
    await tester.pumpAndSettle();
    expect(_actionLabel(tester), 'ESCOLHER LUGAR');
  });

  testWidgets('BI guardado com forma invalida volta a ser pedido',
      (tester) async {
    // Contas antigas podem ter um numero que a regra actual ja nao aceita.
    // Melhor pedi-lo outra vez do que deixar a compra ser recusada pelo
    // servidor depois de escolhido o lugar.
    await _pump(tester, _FakeApi(
      seated: true, departures: _departuresOk, holderDocument: '123'));
    await _chooseRoute(tester);
    await tester.tap(find.text('06:30'));
    await tester.pumpAndSettle();

    expect(find.text('Documento de identificacao'), findsOneWidget);
  });

  testWidgets('no passo do lugar ha sempre botao para avancar', (tester) async {
    await _pump(tester, _FakeApi(seated: true, departures: _departuresOk));
    await _chooseRoute(tester);
    await tester.tap(find.text('06:30'));
    await tester.pumpAndSettle();
    await _preencherDadosDaViagem(tester);
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();

    // Passo 2: a planta esta la e o botao TAMBEM — foi a sua ausencia que
    // deixou o passageiro encravado na versao anterior.
    expect(find.text('PASSO 2 DE 3'), findsOneWidget);
    expect(find.text('1A'), findsOneWidget);
    expect(find.byType(FilledButton), findsOneWidget);
    expect(find.text('Toque num lugar livre para o escolher.'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull);

    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();

    expect(_actionLabel(tester), 'AVANCAR COM O LUGAR 2C');
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNotNull);

    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();

    expect(find.text('PASSO 3 DE 3'), findsOneWidget);
    // O que se esta a pagar tem de estar a vista: veio de dois ecras atras.
    expect(find.text('Lugar 2C'), findsOneWidget);
    expect(find.text('Maputo Junta'), findsOneWidget);
  });

  testWidgets('lugar ocupado nao pode ser escolhido', (tester) async {
    await _pump(tester, _FakeApi(seated: true, departures: _departuresOk));
    await _chooseRoute(tester);
    await tester.tap(find.text('06:30'));
    await tester.pumpAndSettle();
    await _preencherDadosDaViagem(tester);
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();

    // O lugar ocupado nao mostra etiqueta: mostra um X. Tocar-lhe nao escolhe
    // nada e o botao de avancar continua fechado.
    expect(find.text('1D'), findsNothing);
    await tester.tap(find.byIcon(Icons.close).first, warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(find.text('Toque num lugar livre para o escolher.'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull);
  });

  testWidgets('recuar volta ao passo anterior sem perder as escolhas',
      (tester) async {
    await _pump(tester, _FakeApi(seated: true, departures: _departuresOk));
    await _chooseRoute(tester);
    await tester.tap(find.text('06:30'));
    await tester.pumpAndSettle();
    await _preencherDadosDaViagem(tester);
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();
    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();
    expect(find.text('PASSO 3 DE 3'), findsOneWidget);

    // Do pagamento recua-se para o lugar...
    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    expect(find.text('PASSO 2 DE 3'), findsOneWidget);
    expect(_actionLabel(tester), 'AVANCAR COM O LUGAR 2C');

    // ...e do lugar para a viagem, com a partida ainda escolhida.
    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    expect(find.text('PASSO 1 DE 3'), findsOneWidget);
    expect(find.text('06:30'), findsOneWidget);
    expect(_actionLabel(tester), 'ESCOLHER LUGAR');
  });

  testWidgets('mexer no pacote no pagamento nao apaga o lugar escolhido',
      (tester) async {
    await _pump(tester, _FakeApi(seated: true, departures: _departuresOk));
    await _chooseRoute(tester);
    await tester.tap(find.text('06:30'));
    await tester.pumpAndSettle();
    await _preencherDadosDaViagem(tester);
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();
    await tester.tap(find.text('2C'));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();

    // O interruptor do pacote recalcula o preco. Recalcular NAO pode recarregar
    // as partidas: isso largava a viagem e o lugar, e a compra seguia sem eles.
    await tester.tap(find.byType(SwitchListTile));
    await tester.pumpAndSettle();

    expect(find.text('PASSO 3 DE 3'), findsOneWidget);
    expect(find.text('Lugar 2C'), findsOneWidget);
  });

  testWidgets('trocar de destino larga a partida e o lugar ja escolhidos',
      (tester) async {
    await _pump(tester, _FakeApi(seated: true, departures: _departuresOk));
    await _chooseRoute(tester);
    await tester.tap(find.text('06:30'));
    await tester.pumpAndSettle();
    expect(find.text('Contacto de emergencia'), findsOneWidget);

    // Escolher a partida rola ate ao contacto de emergencia; para trocar o
    // destino e preciso subir outra vez.
    await tester.drag(find.byType(ListView), const Offset(0, 600));
    await tester.pumpAndSettle();

    // Trocar o destino: a partida escolhida era da rota anterior e nao pode
    // sobreviver.
    await tester.tap(find.text('Destino'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Xai-Xai Terminal').last);
    await tester.pumpAndSettle();

    expect(find.text('Contacto de emergencia'), findsNothing);
    expect(find.text('Escolha a hora de partida.'), findsOneWidget);
  });
}
