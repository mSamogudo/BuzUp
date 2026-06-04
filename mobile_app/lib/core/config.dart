/// Build-time configuration. Override at runtime via `--dart-define`:
///
///     flutter run --dart-define=BUZUP_API_BASE=https://updigital.co.mz
///
class AppConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'BUZUP_API_BASE',
    defaultValue: 'https://buzup.updigital.co.mz',
  );

  static const apiTimeout = Duration(seconds: 30);
}
