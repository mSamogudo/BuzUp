/// App-wide configuration.
class AppConfig {
  static const String appName = 'BuzUp POS';

  /// Backend base URL. Override via --dart-define=BUZUP_API_BASE=...
  static const String apiBaseUrl = String.fromEnvironment(
    'BUZUP_API_BASE',
    defaultValue: 'https://buzup.updigital.co.mz',
  );

  /// Quanto se espera pela RESPOSTA. Generoso de propósito: um pedido de
  /// pagamento fala com o gateway e demora mesmo.
  static const Duration apiTimeout = Duration(seconds: 25);

  /// Quanto se espera pela resposta da VENDA. Não são os 25 acima, e a
  /// diferença não é gosto: é uma regra que tem de se manter.
  ///
  /// Do lado do servidor a cobrança espera pelo PIN do passageiro — até 60 s
  /// no e-Mola — e o nginx segura a ligação 75 s. Se este número ficar abaixo
  /// desses, a aplicação desliga **antes** de a resposta chegar: o servidor
  /// confirma o pagamento e emite o bilhete, e o agente fica a olhar para um
  /// erro. Aconteceu a 2026-09-12, às 06:32: a operadora respondeu aos 30,6 s
  /// e a aplicação tinha desistido aos 25.
  ///
  /// A cadeia, do mais curto ao mais longo:
  ///
  ///     cobrança 45-60 s  <  nginx 75 s  <  ESTE 80 s  <  gunicorn 200 s
  ///
  /// A aplicação é a última a desistir, de propósito: assim um 504 do nginx
  /// chega-lhe como resposta, e não como silêncio.
  ///
  /// O e-Mola **não tem consulta de estado** (`/search/emola/c2b` dá 404) e a
  /// operadora não nos chama de volta. A resposta síncrona é o único sítio
  /// onde o desfecho se aprende — por isso não se pode encurtar do lado do
  /// servidor, e é aqui que o problema se resolve.
  static const Duration saleTimeout = Duration(seconds: 80);

  /// Quanto se espera para ESTABELECER a ligação (TCP + TLS).
  ///
  /// Separado do de resposta: ligar leva menos de dois segundos mesmo com o
  /// servidor sob carga. Usar os 25 aqui deixava o agente um cheiro de minuto
  /// a olhar para um ecrã parado quando a rede está morta — quando bastavam
  /// doze segundos para lhe dizer que não há rede.
  static const Duration connectTimeout = Duration(seconds: 12);
  static const Duration paymentPollInterval = Duration(seconds: 3);
  static const Duration paymentPollTimeout = Duration(seconds: 180);

  static const Duration heartbeatInterval = Duration(minutes: 1);
}
