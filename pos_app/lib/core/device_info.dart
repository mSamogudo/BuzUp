import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';

import 'storage.dart';

/// O que o Android devolve quando NAO tem numero de serie para dar.
///
/// Desde o Android 10 `Build.getSerial()` esta fechado a aplicacoes normais e
/// a plataforma responde a string literal `"unknown"` — nao vazio. O teste
/// antigo (`isNotEmpty`) dava-a por boa, e por isso TODOS os aparelhos se
/// registavam com o mesmo serial: o primeiro criava o dispositivo e os
/// seguintes entravam por cima dele. Bloquear um bloqueava todos, a posicao
/// GPS do autocarro no mapa vinha de quem tivesse pingado por ultimo, e nao
/// havia forma de saber de que terminal saiu uma venda.
const _seriaisSemValor = {'unknown', 'android', 'null', 'none', '0', 'unavailable'};

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

/// Dados do aparelho para /api/agent/devices/register.
///
/// O serial e o numero de serie real quando existe; caso contrario a
/// identidade guardada da instalacao (ver [_serialUtilizavel]).
Future<DeviceFingerprint> readDeviceFingerprint() async {
  if (!Platform.isAndroid) {
    return DeviceFingerprint(
      // Nao o relogio: um carimbo de tempo dava um aparelho novo em cada
      // arranque e enchia a lista do administrador de dispositivos por aprovar.
      serialNumber: await SecureStore().installationId(),
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
  final serial = await _serialUtilizavel(android.serialNumber);
  return DeviceFingerprint(
    serialNumber: serial,
    modelName: android.model,
    manufacturer: android.manufacturer,
    androidId: android.id,
    deviceType: deviceType,
  );
}

/// Numero de serie real, ou a identidade guardada deste aparelho.
///
/// Nos terminais dedicados (SUNMI, Urovo) o serial le-se e e unico. Num
/// telemovel comum nao se le, e o recurso e um identificador gerado a primeira
/// vez e guardado no armazenamento seguro — unico por instalacao, estavel
/// entre arranques, e o que permite a mesma app servir os dois mundos.
Future<String> _serialUtilizavel(String bruto) async {
  final serial = bruto.trim();
  if (serial.isNotEmpty && !_seriaisSemValor.contains(serial.toLowerCase())) {
    return serial;
  }
  return SecureStore().installationId();
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
