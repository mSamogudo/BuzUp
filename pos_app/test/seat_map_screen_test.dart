import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:pos_app/core/seat_map_screen.dart';

/// Constroi um payload igual ao que `apps/guest_checkouts/seatmap.py` devolve.
Map<String, dynamic> seatMap({
  required int capacity,
  String layout = '2+2',
  int lastRowSeats = 0,
  Set<String> taken = const {},
}) {
  final parts = layout.split('+');
  final leftN = int.parse(parts[0]);
  final rightN = int.parse(parts[1]);
  final perRow = leftN + rightN;
  const letters = 'ABCDEFGH';

  final body = lastRowSeats > 0 ? capacity - lastRowSeats : capacity;
  final rows = <Map<String, dynamic>>[];
  var placed = 0;
  var rowNumber = 0;
  while (placed < body) {
    rowNumber++;
    final take = (perRow < body - placed) ? perRow : body - placed;
    final seats = [for (var i = 0; i < take; i++) '$rowNumber${letters[i]}'];
    Map<String, dynamic> cell(String s) => {'label': s, 'occupied': taken.contains(s)};
    rows.add({
      'row': rowNumber,
      'left': seats.take(leftN).map(cell).toList(),
      'right': seats.skip(leftN).map(cell).toList(),
      'full_width': false,
    });
    placed += take;
  }
  if (lastRowSeats > 0) {
    rowNumber++;
    rows.add({
      'row': rowNumber,
      'left': [
        for (var i = 0; i < lastRowSeats; i++)
          {'label': '$rowNumber${letters[i]}', 'occupied': taken.contains('$rowNumber${letters[i]}')},
      ],
      'right': <Map<String, dynamic>>[],
      'full_width': true,
    });
  }
  return {'has_seat_map': true, 'layout': layout, 'capacity': capacity, 'rows': rows};
}

Future<List<String>?> pumpPicker(
  WidgetTester tester, {
  required Map<String, dynamic> map,
  required int maxPick,
  Size screen = const Size(411, 866),
}) async {
  tester.view.physicalSize = screen;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  List<String>? result;
  await tester.pumpWidget(MaterialApp(
    home: Builder(
      builder: (ctx) => Scaffold(
        body: Center(
          child: ElevatedButton(
            onPressed: () async {
              result = await SeatMapScreen.pick(ctx, seatMap: map, maxPick: maxPick);
            },
            child: const Text('abrir'),
          ),
        ),
      ),
    ),
  ));
  await tester.tap(find.text('abrir'));
  await tester.pumpAndSettle();
  return result;
}

void main() {
  // Os autocarros reais da operacao: 2+2 de 60, 1+2 de 45 (interprovincial
  // com banco individual), 3+2 de 65 e ultima fila corrida.
  final frotas = <String, Map<String, dynamic>>{
    '2+2 / 60': seatMap(capacity: 60),
    '1+2 / 45': seatMap(capacity: 45, layout: '1+2'),
    '3+2 / 65': seatMap(capacity: 65, layout: '3+2'),
    '2+2 / 62 com fila corrida': seatMap(capacity: 62, layout: '2+2', lastRowSeats: 5),
    '2+2 / 16 (mini)': seatMap(capacity: 16),
  };

  for (final entry in frotas.entries) {
    testWidgets('desenha sem estourar o ecra: ${entry.key}', (tester) async {
      await pumpPicker(tester, map: entry.value, maxPick: 1);
      expect(tester.takeException(), isNull, reason: 'excepcao ao desenhar ${entry.key}');
    });

    testWidgets('desenha em ecra pequeno: ${entry.key}', (tester) async {
      await pumpPicker(tester, map: entry.value, maxPick: 1,
          screen: const Size(320, 568));
      expect(tester.takeException(), isNull, reason: 'ecra pequeno: ${entry.key}');
    });
  }

  testWidgets('escolher um lugar e confirmar devolve o lugar', (tester) async {
    final map = seatMap(capacity: 60);
    List<String>? result;
    tester.view.physicalSize = const Size(411, 866);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(MaterialApp(
      home: Builder(
        builder: (ctx) => Scaffold(
          body: Center(
            child: ElevatedButton(
              onPressed: () async {
                result = await SeatMapScreen.pick(ctx, seatMap: map, maxPick: 1);
              },
              child: const Text('abrir'),
            ),
          ),
        ),
      ),
    ));
    await tester.tap(find.text('abrir'));
    await tester.pumpAndSettle();

    expect(find.text('1A'), findsOneWidget, reason: 'o lugar 1A tem de estar visivel');
    await tester.tap(find.text('1A'));
    await tester.pumpAndSettle();

    expect(find.text('CONFIRMAR'), findsOneWidget,
        reason: 'com o lugar escolhido o botao tem de ficar activo');
    await tester.tap(find.text('CONFIRMAR'));
    await tester.pumpAndSettle();

    expect(result, ['1A']);
  });

  testWidgets('lugar ocupado nao pode ser escolhido', (tester) async {
    final map = seatMap(capacity: 60, taken: {'1A'});
    await pumpPicker(tester, map: map, maxPick: 1);
    await tester.tap(find.byType(SeatMapScreen).first, warnIfMissed: false);
    // Ocupado desenha um X, nao a etiqueta.
    expect(find.text('1A'), findsNothing);
    expect(find.text('CONFIRMAR'), findsNothing,
        reason: 'sem lugar escolhido o botao nao pode dizer CONFIRMAR');
  });

  testWidgets('com maxPick=1 tocar noutro lugar troca a escolha', (tester) async {
    final map = seatMap(capacity: 60);
    await pumpPicker(tester, map: map, maxPick: 1);
    await tester.tap(find.text('1A'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('1B'));
    await tester.pumpAndSettle();
    expect(find.text('1/1'), findsOneWidget, reason: 'devia continuar com 1 lugar');
    expect(tester.takeException(), isNull);
  });

  testWidgets('venda de 3 bilhetes so confirma com 3 lugares', (tester) async {
    final map = seatMap(capacity: 60);
    List<String>? result;
    tester.view.physicalSize = const Size(411, 866);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(MaterialApp(
      home: Builder(
        builder: (ctx) => Scaffold(
          body: Center(
            child: ElevatedButton(
              onPressed: () async {
                result = await SeatMapScreen.pick(ctx, seatMap: map, maxPick: 3);
              },
              child: const Text('abrir'),
            ),
          ),
        ),
      ),
    ));
    await tester.tap(find.text('abrir'));
    await tester.pumpAndSettle();

    expect(find.text('FALTAM 3'), findsOneWidget);
    await tester.tap(find.text('1A'));
    await tester.pumpAndSettle();
    expect(find.text('FALTAM 2'), findsOneWidget);
    await tester.tap(find.text('1B'));
    await tester.pumpAndSettle();
    expect(find.text('FALTA 1'), findsOneWidget, reason: 'singular com 1 em falta');
    await tester.tap(find.text('2A'));
    await tester.pumpAndSettle();

    expect(find.text('3/3'), findsOneWidget);
    await tester.tap(find.text('CONFIRMAR'));
    await tester.pumpAndSettle();
    expect(result, ['1A', '1B', '2A']);
  });

  testWidgets('com varios lugares, tocar num escolhido larga-o', (tester) async {
    final map = seatMap(capacity: 60);
    await pumpPicker(tester, map: map, maxPick: 2);
    await tester.tap(find.text('1A'));
    await tester.pumpAndSettle();
    // Escolhido, o lugar passa a aparecer duas vezes: no banco e no resumo
    // em baixo. O primeiro na arvore e o banco.
    await tester.tap(find.text('1A').first);
    await tester.pumpAndSettle();
    expect(find.text('0/2'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('reabrir mantem os lugares ja escolhidos', (tester) async {
    final map = seatMap(capacity: 60);
    tester.view.physicalSize = const Size(411, 866);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(MaterialApp(
      home: Builder(
        builder: (ctx) => Scaffold(
          body: Center(
            child: ElevatedButton(
              onPressed: () => SeatMapScreen.pick(ctx,
                  seatMap: map, maxPick: 2, initialPicked: const ['1A', '1B']),
              child: const Text('abrir'),
            ),
          ),
        ),
      ),
    ));
    await tester.tap(find.text('abrir'));
    await tester.pumpAndSettle();
    expect(find.text('2/2'), findsOneWidget);
    expect(find.text('CONFIRMAR'), findsOneWidget);
  });

  testWidgets('todos os lugares sao alcancaveis (rolagem quando preciso)', (tester) async {
    // 1+2 de 45 = 15 filas; a ultima tem de dar para escolher.
    final map = seatMap(capacity: 45, layout: '1+2');
    await pumpPicker(tester, map: map, maxPick: 1, screen: const Size(320, 568));
    final ultimo = find.text('15C');
    await tester.scrollUntilVisible(ultimo, 60, scrollable: find.byType(Scrollable).last);
    await tester.tap(ultimo);
    await tester.pumpAndSettle();
    expect(find.text('CONFIRMAR'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
