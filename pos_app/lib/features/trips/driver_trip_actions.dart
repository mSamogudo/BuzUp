import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/feedback.dart';
import '../../core/location.dart';
import '../../core/providers.dart';
import '../../core/theme.dart';

/// O ciclo de vida de uma viagem, num sítio só.
///
/// Vivia dentro do ecrã de viagens. Passou para aqui quando a página inicial
/// também ganhou a acção: duplicá-la era duplicar o pedido de permissão de
/// localização e a identificação do terminal — e esquecer um deles no caminho
/// novo faria o autocarro arrancar invisível no mapa dos passageiros, sem
/// ninguém dar por isso.
class DriverTripActions {
  /// O passo seguinte de uma viagem, a partir do estado em que está.
  ///
  /// Devolve `null` quando não há nada a fazer (concluída, cancelada).
  ///
  /// **São três momentos e não um.** Abrir o EMBARQUE não é partir: entre uma
  /// coisa e outra o autocarro está parado a encher, e foi por isso que os dois
  /// passos foram separados — com um botão só, a hora de saída ficava com o
  /// instante em que o primeiro passageiro subiu, e não com o da partida.
  static ({String action, String label})? next(String status) => switch (status) {
        'scheduled' => (action: 'start', label: 'ABRIR EMBARQUE'),
        'boarding' => (action: 'depart', label: 'INICIAR VIAGEM'),
        'paused' => (action: 'resume', label: 'RETOMAR'),
        _ => null,
      };

  /// Executa uma acção do ciclo. Devolve a resposta, ou `null` se falhou.
  ///
  /// `context` serve só para mostrar avisos; quem chama trata do que fazer a
  /// seguir. Invalida a lista de viagens no fim, para todos os ecrãs que a
  /// mostram ficarem coerentes.
  static Future<Map<String, dynamic>?> run(
    WidgetRef ref,
    BuildContext context,
    int tripId,
    String action,
  ) async {
    try {
      // No arranque, o terminal identifica-se: passa a ser a fonte da posicao
      // do autocarro no mapa dos passageiros.
      final serial = action == 'start'
          ? await ref.read(secureStoreProvider).getDeviceSerial()
          : null;
      // Abrir o embarque e o momento em que o rastreio passa a valer: se a
      // permissao ainda nao foi dada, pede-se agora, e avisa-se se for
      // recusada — senao a viagem arranca e o autocarro fica invisivel no
      // mapa dos passageiros sem ninguem dar por isso.
      if (action == 'start') {
        final readiness = await DeviceLocation.ensurePermission();
        if (readiness != LocationReadiness.ok && context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(DeviceLocation.describe(readiness)),
              backgroundColor: const Color(0xFFB45309),
              action: SnackBarAction(
                label: 'Corrigir',
                textColor: Colors.white,
                onPressed: () => DeviceLocation.openSettingsFor(readiness),
              ),
            ),
          );
        }
      }
      final res = await ref
          .read(agentApiProvider)
          .driverTripAction(tripId, action, deviceSerial: serial);
      await AppFeedback.success();
      ref.invalidate(driverTripsProvider);
      return res;
    } on DioException catch (e) {
      await AppFeedback.error();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ApiClient.extractError(e)),
            backgroundColor: BuzUpColors.danger,
          ),
        );
      }
      return null;
    }
  }
}
