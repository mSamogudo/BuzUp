import 'package:flutter_test/flutter_test.dart';
import 'package:pos_app/core/config.dart';

/// Dois em cada três pagamentos por carteira falhavam, e 12 das 16 falhas
/// eram passageiros que não marcavam o PIN a tempo — todas entre 42,2 e 42,9
/// segundos, com a mesma frase do broker. O terminal nunca lhes disse que
/// havia relógio.
///
/// Estes testes fixam as duas regras que o ecrã usa para o mostrar: qual
/// carteira vai tocar, e quanto tempo há. Se alguém as mudar sem medir de
/// novo, o número no ecrã passa a mentir — e um relógio que mente é pior do
/// que relógio nenhum.
void main() {
  group('carteira, pelo prefixo', () {
    test('84 e 85 são Vodacom — M-Pesa', () {
      expect(AppConfig.carteiraDoNumero('848818277'), 'M-Pesa');
      expect(AppConfig.carteiraDoNumero('851576568'), 'M-Pesa');
    });

    test('86 e 87 são Movitel — e-Mola', () {
      expect(AppConfig.carteiraDoNumero('869966622'), 'e-Mola');
      expect(AppConfig.carteiraDoNumero('876671100'), 'e-Mola');
    });

    test('o indicativo 258 não muda a leitura', () {
      expect(AppConfig.carteiraDoNumero('258869966622'), 'e-Mola');
      expect(AppConfig.carteiraDoNumero('+258 84 881 8277'), 'M-Pesa');
    });

    test('prefixo que não é de carteira devolve vazio, não adivinha', () {
      expect(AppConfig.carteiraDoNumero('821234567'), '');
      expect(AppConfig.carteiraDoNumero(''), '');
    });
  });

  group('janela do PIN', () {
    test('e-Mola são 42 segundos — o que se mediu em produção', () {
      expect(AppConfig.janelaDoPin('869966622').inSeconds, 42);
    });

    test('M-Pesa são 45 — o nosso timeout, que é quem desiste primeiro', () {
      expect(AppConfig.janelaDoPin('848818277').inSeconds, 45);
    });

    test('número desconhecido não fica sem relógio', () {
      expect(AppConfig.janelaDoPin('821234567').inSeconds, greaterThan(0),
          reason: 'sem janela o ecrã não teria nada para contar');
    });

    test('a janela nunca ultrapassa o tempo que o servidor espera', () {
      // O servidor larga a cobrança aos 45s (M-Pesa) e 60s (e-Mola). Uma
      // contagem mais longa que isso prometia ao passageiro tempo que já não
      // existe.
      for (final n in ['848818277', '869966622']) {
        expect(AppConfig.janelaDoPin(n).inSeconds, lessThanOrEqualTo(60));
      }
    });
  });
}
