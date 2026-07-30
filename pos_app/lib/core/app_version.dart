import 'package:package_info_plus/package_info_plus.dart';

/// Versão real da app, lida do pacote instalado.
///
/// O registo do terminal e o heartbeat enviavam `'1.0.0'` escrito à mão
/// enquanto a app ia em 1.3.9+13: o portal mostrava a versão errada em todos
/// os terminais, e era impossível saber quem já tinha actualizado.
class AppVersion {
  static String _label = "";
  static String _version = "";
  static int _buildNumber = 0;

  /// "1.3.9+13" — para mostrar ao utilizador.
  static String get label => _label;

  /// "1.3.9" — o que o backend guarda como versão do terminal.
  static String get version => _version.isEmpty ? "0.0.0" : _version;

  /// Número de build já sem o deslocamento por ABI dos builds split-per-abi
  /// (abi*1000 + build, ex.: 2013 -> 13).
  static int get buildNumber => _buildNumber % 1000;

  static Future<void> load() async {
    try {
      final info = await PackageInfo.fromPlatform();
      _version = info.version;
      _buildNumber = int.tryParse(info.buildNumber) ?? 0;
      _label = "${info.version}+${info.buildNumber}";
    } catch (_) {
      _label = "";
    }
  }
}
