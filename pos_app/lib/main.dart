import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Fullscreen: hide system status + navigation bars to maximize screen real
  // estate on SUNMI/Urovo POS terminals (small 5"–6" displays).
  await SystemChrome.setEnabledSystemUIMode(
    SystemUiMode.immersiveSticky,
    overlays: [],
  );
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    systemNavigationBarColor: Colors.transparent,
  ));
  runApp(const ProviderScope(child: PosApp()));
}
