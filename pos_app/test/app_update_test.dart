import 'package:flutter_test/flutter_test.dart';
import 'package:pos_app/core/app_update.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// O 1.9.1 corrigia uma cobrança que parecia falhar ao operador enquanto o
/// passageiro era debitado. Esteve dois dias publicado sem chegar a um único
/// terminal, porque a verificação corria uma vez por arranque da app e um
/// "Agora não" calava-a para sempre.
///
/// Estes testes fixam o meio-termo: um "Agora não" é respeitado durante o dia
/// de trabalho, e deixa de o ser a seguir. Nem insistir de hora a hora — o
/// operador aprende a fechar a caixa sem ler — nem calar para sempre.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('sem adiamento nenhum, pergunta-se', () async {
    expect(await estaAdiada(38), isFalse);
  });

  test('logo a seguir a um "Agora nao", nao se volta a perguntar', () async {
    await adiar(38);
    expect(await estaAdiada(38), isTrue);
  });

  test('adiar uma versao nao cala a seguinte', () async {
    await adiar(38);
    expect(await estaAdiada(39), isFalse,
        reason: 'senao uma correccao urgente ficava presa atras de um "Agora nao" antigo');
  });

  test('o adiamento expira — nao e um silencio definitivo', () async {
    final ontem = DateTime.now().subtract(const Duration(hours: 13));
    SharedPreferences.setMockInitialValues({
      'actualizacao_adiada': '38|${ontem.toIso8601String()}',
    });
    expect(await estaAdiada(38), isFalse,
        reason: 'passadas 12h o terminal tem de voltar a ser oferecido');
  });

  test('marca corrompida nao cala a verificacao', () async {
    SharedPreferences.setMockInitialValues({'actualizacao_adiada': 'lixo'});
    expect(await estaAdiada(38), isFalse,
        reason: 'na duvida pergunta-se; o custo de insistir e menor que o de calar');
  });
}
