import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart' show initializeDateFormatting;

import 'app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // DateFormat with non-en locale (pt_PT, en_US) needs symbols pre-loaded.
  await initializeDateFormatting('pt_PT');
  await initializeDateFormatting('en_US');
  // Edge-to-edge: draw under status & nav bars; gestures show them back on
  // swipe but the app reclaims fullscreen automatically afterwards.
  await SystemChrome.setEnabledSystemUIMode(
    SystemUiMode.edgeToEdge,
    overlays: [],
  );
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    systemNavigationBarColor: Colors.transparent,
  ));
  runApp(const ProviderScope(child: MobileApp()));
}
