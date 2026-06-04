/// App-wide configuration.
class AppConfig {
  static const String appName = 'BuzUp POS';

  /// Backend base URL. Override via --dart-define=BUZUP_API_BASE=...
  static const String apiBaseUrl = String.fromEnvironment(
    'BUZUP_API_BASE',
    defaultValue: 'https://buzup.updigital.co.mz',
  );

  static const Duration apiTimeout = Duration(seconds: 25);
  static const Duration paymentPollInterval = Duration(seconds: 3);
  static const Duration paymentPollTimeout = Duration(seconds: 180);

  static const Duration heartbeatInterval = Duration(minutes: 1);
}
