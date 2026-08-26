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
