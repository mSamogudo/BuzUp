import 'dart:async';

import 'package:geolocator/geolocator.dart';

/// Estado do acesso à localização do dispositivo.
enum LocationReadiness {
  /// Há permissão e o GPS está ligado: o autocarro aparece no mapa.
  ok,

  /// Permissão concedida mas a localização do telefone está desligada.
  serviceOff,

  /// O operador recusou desta vez; volta a poder ser pedido.
  denied,

  /// Recusado permanentemente — só se resolve nas definições do Android.
  deniedForever,
}

/// Localização do POS, usada no heartbeat que alimenta o mapa em tempo real
/// da app do passageiro.
///
/// O ponto delicado é a permissão: no Android começa sempre em `denied`, e
/// `checkPermission()` sozinho nunca a altera — limita-se a confirmar que não
/// existe. Sem `requestPermission()` o diálogo do sistema nunca aparece, o
/// heartbeat sai sem coordenadas e o autocarro simplesmente não surge no mapa,
/// sem qualquer erro visível. Por isso o pedido é explícito e o resultado é
/// devolvido ao ecrã, para o agente perceber que não está a ser seguido.
class DeviceLocation {
  const DeviceLocation._();

  /// Pede permissão se ainda não a houver e diz em que estado ficou.
  /// Seguro para chamar repetidamente: já concedida, não mostra diálogo.
  static Future<LocationReadiness> ensurePermission() async {
    var permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.deniedForever) {
      return LocationReadiness.deniedForever;
    }
    if (permission != LocationPermission.always &&
        permission != LocationPermission.whileInUse) {
      return LocationReadiness.denied;
    }

    // A permissão não chega: o GPS do aparelho pode estar desligado.
    if (!await Geolocator.isLocationServiceEnabled()) {
      return LocationReadiness.serviceOff;
    }
    return LocationReadiness.ok;
  }

  /// Posição actual, ou `null` se não houver permissão, o GPS estiver
  /// desligado ou a leitura demorar demasiado.
  ///
  /// Nunca lança: o heartbeat não pode falhar por causa do GPS — perder a
  /// posição de um minuto é aceitável, perder o heartbeat marcaria o
  /// dispositivo como offline.
  static Future<Position?> current({
    Duration timeout = const Duration(seconds: 5),
  }) async {
    try {
      final permission = await Geolocator.checkPermission();
      if (permission != LocationPermission.always &&
          permission != LocationPermission.whileInUse) {
        return null;
      }
      if (!await Geolocator.isLocationServiceEnabled()) return null;

      return await Geolocator.getCurrentPosition(
        locationSettings: LocationSettings(
          // Chega para desenhar o autocarro no mapa e poupa bateria num
          // aparelho que passa o dia inteiro ligado.
          accuracy: LocationAccuracy.medium,
          timeLimit: timeout,
        ),
      ).timeout(timeout);
    } catch (_) {
      return null;
    }
  }

  /// Abre as definições certas para o operador corrigir o problema.
  static Future<void> openSettingsFor(LocationReadiness readiness) async {
    if (readiness == LocationReadiness.serviceOff) {
      await Geolocator.openLocationSettings();
    } else {
      await Geolocator.openAppSettings();
    }
  }

  static String describe(LocationReadiness readiness) {
    switch (readiness) {
      case LocationReadiness.ok:
        return 'Localizacao activa.';
      case LocationReadiness.serviceOff:
        return 'Ligue a localizacao do aparelho para o autocarro aparecer no mapa dos passageiros.';
      case LocationReadiness.denied:
        return 'Sem permissao de localizacao: o autocarro nao aparece no mapa dos passageiros.';
      case LocationReadiness.deniedForever:
        return 'Permissao de localizacao bloqueada. Active-a nas definicoes da aplicacao.';
    }
  }
}
