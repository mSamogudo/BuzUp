import 'package:flutter/material.dart';

/// BusUp POS palette — alinhada ao portal: azul primario, fundo branco (claro)
/// / azul-preto (escuro). Laranja fica como acento pontual.
class BuzUpColors {
  static const navy = Color(0xFF071E49);
  static const navyDark = Color(0xFF051538);
  static const blue = Color(0xFF1D5FA7); // primario (claro) — portal --app-accent
  static const blueDark = Color(0xFF2D8CF0); // primario (escuro)
  static const blueDeep = Color(0xFF0D3B66);
  static const orange = Color(0xFFE47B11);
  static const orangeLight = Color(0xFFF59E3D);
  static const cream = Color(0xFFF7F4EE);
  static const success = Color(0xFF2A9D8F);
  static const danger = Color(0xFFD62828);
}

class BuzUpTheme {
  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: BuzUpColors.blue,
      primary: BuzUpColors.blue,
      secondary: BuzUpColors.orange,
      brightness: Brightness.light,
      surface: Colors.white,
      onPrimary: Colors.white,
    );
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: const Color(0xFFF4F6FA),
      colorScheme: scheme,
      appBarTheme: const AppBarTheme(
        backgroundColor: BuzUpColors.navy,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: const CardThemeData(
        elevation: 1,
        margin: EdgeInsets.zero,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: BuzUpColors.blue,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          textStyle: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
        filled: true,
        fillColor: Colors.white,
      ),
      dividerColor: Colors.grey.shade300,
    );
  }

  static ThemeData dark() {
    final scheme = ColorScheme.fromSeed(
      seedColor: BuzUpColors.blue,
      primary: BuzUpColors.blueDark,
      secondary: BuzUpColors.orange,
      brightness: Brightness.dark,
      surface: const Color(0xFF12203F),
      onPrimary: const Color(0xFF06101F),
    );
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: BuzUpColors.navyDark,
      colorScheme: scheme,
      appBarTheme: const AppBarTheme(
        backgroundColor: BuzUpColors.navyDark,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: const CardThemeData(
        elevation: 0,
        color: Color(0xFF12203F),
        margin: EdgeInsets.zero,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: BuzUpColors.blueDark,
          foregroundColor: const Color(0xFF06101F),
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          textStyle: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
        filled: true,
        fillColor: Color(0xFF1A2A4E),
      ),
      dividerColor: Colors.white12,
    );
  }
}
