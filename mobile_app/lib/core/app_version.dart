import 'package:package_info_plus/package_info_plus.dart';

/// Versão real da app, lida do pacote instalado.
///
/// Estava escrita à mão no ecrã de perfil e ficou desactualizada ("v0.3" com
/// a app em 0.4.8) — o suporte recebia versões erradas dos utilizadores.
class AppVersion {
  static String _label = "";

  static String get label => _label;

  static Future<void> load() async {
    try {
      final info = await PackageInfo.fromPlatform();
      _label = "${info.version}+${info.buildNumber}";
    } catch (_) {
      _label = "";
    }
  }
}
