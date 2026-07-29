import 'dart:math';

import 'package:dio/dio.dart';

/// Chaves de idempotência para operações que mexem em dinheiro.
///
/// O problema que isto resolve: o agente carrega em "Confirmar", a rede cai a
/// meio e ele volta a carregar. Sem chave, o backend trata a segunda tentativa
/// como uma operação nova e o passageiro é debitado (ou cobrado) duas vezes.
/// Com chave, o servidor reconhece a repetição e devolve o resultado da
/// primeira — o dinheiro só se move uma vez.
///
/// A regra que torna isto correcto é *quando* a chave muda:
///
///  - **mantém-se** enquanto a tentativa for ambígua (timeout, rede em baixo,
///    5xx) — é exactamente aí que a repetição duplica cobranças;
///  - **roda** depois de a operação terminar de forma conhecida, com sucesso
///    ou com recusa do servidor — aí a tentativa seguinte é mesmo nova, e
///    reutilizar a chave faria o servidor devolver o resultado antigo.
///
/// Gerar a chave dentro do cliente HTTP não serviria: cada repetição criaria
/// uma chave nova e a protecção desaparecia. Por isso vive no ecrã, ligada à
/// intenção do utilizador.
class IdempotencyScope {
  IdempotencyScope();

  static final Random _rng = Random.secure();

  String? _key;
  String _signature = '';

  /// Chave da tentativa em curso, criada na primeira invocação e estável nas
  /// repetições seguintes até alguém chamar [rotate].
  String get key => _key ??= _generate();

  /// Chave ligada aos dados da operação (cartão, valor, pacote...).
  ///
  /// Repetir a mesma operação devolve a mesma chave — é o que impede a dupla
  /// cobrança. Mas se o agente corrigir o valor antes de tentar de novo, a
  /// assinatura muda e a chave roda sozinha: sem isto o servidor reconhecia a
  /// chave antiga e reponderia com a recarga do valor errado, ignorando a
  /// correcção em silêncio.
  String keyFor(String signature) {
    if (signature != _signature) {
      _signature = signature;
      _key = null;
    }
    return key;
  }

  /// Descarta a chave: a próxima operação passa a ser tratada como nova.
  /// Chamar após sucesso ou após uma recusa explícita do servidor.
  void rotate() {
    _key = null;
    _signature = '';
  }

  static String _generate() {
    const hex = '0123456789abcdef';
    final buffer = StringBuffer('pos-');
    for (var i = 0; i < 32; i++) {
      buffer.write(hex[_rng.nextInt(16)]);
    }
    return buffer.toString();
  }
}

/// Verdadeiro quando o pedido falhou sem que se saiba se o servidor o chegou a
/// processar — timeout, quebra de ligação ou 5xx. Nestes casos a chave tem de
/// ser reutilizada na repetição, senão o passageiro pode ser cobrado duas vezes.
///
/// Um 4xx é o caso oposto: o servidor respondeu e recusou, logo nada se moveu
/// e a tentativa seguinte é genuinamente nova.
bool isAmbiguousFailure(Object error) {
  if (error is! DioException) {
    // Erro inesperado do lado do cliente: assume-se o pior e mantém-se a chave.
    return true;
  }
  switch (error.type) {
    case DioExceptionType.connectionTimeout:
    case DioExceptionType.sendTimeout:
    case DioExceptionType.receiveTimeout:
    case DioExceptionType.connectionError:
    case DioExceptionType.unknown:
      return true;
    case DioExceptionType.badResponse:
      final status = error.response?.statusCode ?? 0;
      return status >= 500;
    case DioExceptionType.cancel:
    case DioExceptionType.badCertificate:
      return false;
  }
}
