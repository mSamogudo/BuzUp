import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/app_version.dart';
import 'core/device_info.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Antes do primeiro registo/heartbeat: e essa a versao que o portal mostra.
  await AppVersion.load();
  // Ecrã cheio só nos terminais dedicados (SUNMI/Urovo, 5"–6"), onde cada
  // pixel conta e não há outra app a usar. Num telemóvel comum esconder a
  // barra de estado e os botões de navegação é hostil: o agente perde relógio,
  // bateria e o botão para voltar — e a app POS corre bem em telemóvel porque
  // não imprime nada.
  final dedicatedTerminal = await isDedicatedPosTerminal();
  if (dedicatedTerminal) {
    await SystemChrome.setEnabledSystemUIMode(
      SystemUiMode.immersiveSticky,
      overlays: [],
    );
  } else {
    await SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  }
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    systemNavigationBarColor: Colors.transparent,
  ));
  runApp(const ProviderScope(child: PosApp()));
}
