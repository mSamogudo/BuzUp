import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pos_app/core/idempotency.dart';

/// A regra que impede cobranças duplicadas está toda no *quando* a chave muda.
/// Estes testes fixam esse comportamento: um engano aqui custa dinheiro real a
/// passageiros, e não daria erro nenhum em produção — só um débito a mais.
void main() {
  final req = RequestOptions(path: '/api/agent/topups/wallet/');

  group('IdempotencyScope', () {
    test('repetir a mesma operacao reutiliza a chave', () {
      final scope = IdempotencyScope();
      final first = scope.keyFor('topup:CARD1:100');
      final retry = scope.keyFor('topup:CARD1:100');
      expect(retry, first, reason: 'a repeticao tem de ser reconhecida como a mesma operacao');
    });

    test('mudar o valor gera chave nova', () {
      final scope = IdempotencyScope();
      final original = scope.keyFor('topup:CARD1:100');
      final corrigido = scope.keyFor('topup:CARD1:250');
      expect(corrigido, isNot(original),
          reason: 'senao o servidor respondia com a recarga de 100 e ignorava a correcao');
    });

    test('rotate faz da operacao seguinte uma nova', () {
      final scope = IdempotencyScope();
      final primeira = scope.keyFor('val:CARD1:7');
      scope.rotate();
      final segunda = scope.keyFor('val:CARD1:7');
      expect(segunda, isNot(primeira),
          reason: 'um segundo embarque do mesmo cartao e uma viagem nova e deve ser cobrado');
    });

    test('cada scope gera chaves distintas', () {
      expect(IdempotencyScope().key, isNot(IdempotencyScope().key));
    });
  });

  group('isAmbiguousFailure', () {
    test('timeouts e falhas de ligacao sao ambiguos', () {
      for (final type in [
        DioExceptionType.connectionTimeout,
        DioExceptionType.sendTimeout,
        DioExceptionType.receiveTimeout,
        DioExceptionType.connectionError,
        DioExceptionType.unknown,
      ]) {
        expect(isAmbiguousFailure(DioException(requestOptions: req, type: type)), isTrue,
            reason: '$type: o servidor pode ter processado, a chave tem de sobreviver');
      }
    });

    test('5xx e ambiguo — o pedido chegou e pode ter sido gravado', () {
      final e = DioException(
        requestOptions: req,
        type: DioExceptionType.badResponse,
        response: Response(requestOptions: req, statusCode: 502),
      );
      expect(isAmbiguousFailure(e), isTrue);
    });

    test('4xx nao e ambiguo — o servidor recusou e nada se moveu', () {
      for (final status in [400, 402, 404, 409]) {
        final e = DioException(
          requestOptions: req,
          type: DioExceptionType.badResponse,
          response: Response(requestOptions: req, statusCode: status),
        );
        expect(isAmbiguousFailure(e), isFalse, reason: '$status devia libertar a chave');
      }
    });

    test('erro nao-Dio assume o pior e mantem a chave', () {
      expect(isAmbiguousFailure(StateError('boom')), isTrue);
    });
  });
}
