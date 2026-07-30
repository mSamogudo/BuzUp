import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';

class DeviceFingerprint {
  DeviceFingerprint({
    required this.serialNumber,
    required this.modelName,
    required this.manufacturer,
    required this.androidId,
    required this.deviceType,
  });

  final String serialNumber;
  final String modelName;
  final String manufacturer;
  final String androidId;
  final String deviceType;
}

/// Returns device data suitable for /api/agent/devices/register.
/// Falls back to a deterministic identifier if real serial cannot be read.
Future<DeviceFingerprint> readDeviceFingerprint() async {
  if (!Platform.isAndroid) {
    return DeviceFingerprint(
      serialNumber: 'NON-ANDROID-${DateTime.now().millisecondsSinceEpoch}',
      modelName: Platform.operatingSystem,
      manufacturer: 'unknown',
      androidId: '',
      deviceType: 'mobile_app',
    );
  }

  final info = DeviceInfoPlugin();
  final android = await info.androidInfo;
  final manufacturer = (android.manufacturer).toLowerCase();
  String deviceType = 'mobile_app';
  if (manufacturer.contains('sunmi')) {
    deviceType = 'sunmi_v2s_pos';
  } else if (manufacturer.contains('urovo')) {
    deviceType = 'urovo_i9100_pos';
  }
  final serial = android.serialNumber.isNotEmpty
      ? android.serialNumber
      : 'AND-${android.id}';
  return DeviceFingerprint(
    serialNumber: serial,
    modelName: android.model,
    manufacturer: android.manufacturer,
    androidId: android.id,
    deviceType: deviceType,
  );
}

/// `true` num terminal POS dedicado (SUNMI/Urovo), `false` em telemovel comum.
///
/// Governa o modo de ecra cheio: no terminal esconder as barras do sistema
/// aproveita o ecra pequeno; num telemovel tira ao agente o relogio, a bateria
/// e o botao de voltar sem nada em troca.
Future<bool> isDedicatedPosTerminal() async {
  if (!Platform.isAndroid) return false;
  try {
    final android = await DeviceInfoPlugin().androidInfo;
    final make = android.manufacturer.toLowerCase();
    return make.contains('sunmi') || make.contains('urovo');
  } catch (_) {
    return false;  // na duvida, respeitar as barras do sistema
  }
}
