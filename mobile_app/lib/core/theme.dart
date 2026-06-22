import 'package:flutter/material.dart';

/// BusUp design tokens — alinhados ao portal: azul primario, fundo branco
/// (modo claro) / quase-preto (modo escuro). Laranja fica como acento pontual.
class BuzUpColors {
  // Marca passou a AZUL: estas constantes (historicamente "orange") sao agora
  // tons de azul para que todas as referencias antigas fiquem azuis.
  static const orange = Color(0xFF1D5FA7);
  static const orangeDark = Color(0xFF2D8CF0);
  static const blue = Color(0xFF1D5FA7); // primario (claro) — portal --app-accent
  static const blueDark = Color(0xFF2D8CF0); // primario (escuro) — portal dark accent
  static const blueDeep = Color(0xFF0D3B66);
  static const navy = Color(0xFF071E49);
  static const navyDark = Color(0xFF1A2A4E);
  static const cream = Color(0xFFF7F4EE);
  static const bgLight = Color(0xFFF4F6FA); // fundo claro azul-branco
  static const success = Color(0xFF1FB04A);
  static const danger = Color(0xFFEF4444);
  static const muted = Color(0xFF6B6356);
  static const mutedDark = Color(0xFF8F94A0);
  static const border = Color(0xFFE7E1D4);
  static const borderDark = Color(0xFF27272A);
  static const surfaceLight = Colors.white;
  static const surfaceDark = Color(0xFF15181F);
  static const scaffoldDark = Color(0xFF09090B); // azul-preto, portal --app-bg dark
}

class BuzUpTheme {
  static ThemeData light() {
    final base = ThemeData.light(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: BuzUpColors.bgLight,
      colorScheme: base.colorScheme.copyWith(
        primary: BuzUpColors.blue,
        onPrimary: Colors.white,
        secondary: BuzUpColors.orange,
        onSecondary: Colors.white,
        surface: BuzUpColors.surfaceLight,
        onSurface: const Color(0xFF15191E),
        error: BuzUpColors.danger,
        outline: BuzUpColors.border,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: BuzUpColors.bgLight,
        elevation: 0,
        scrolledUnderElevation: 0,
        foregroundColor: Color(0xFF15191E),
        titleTextStyle: TextStyle(
          color: Color(0xFF15191E),
          fontSize: 17,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.2,
        ),
      ),
      cardTheme: CardThemeData(
        color: BuzUpColors.surfaceLight,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: BuzUpColors.border),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: BuzUpColors.surfaceLight,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: BuzUpColors.border)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: BuzUpColors.border)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: BuzUpColors.blue, width: 2)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: BuzUpColors.blue,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          minimumSize: const Size.fromHeight(50),
          textStyle: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.3),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: BuzUpColors.blue,
          side: const BorderSide(color: BuzUpColors.border),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          minimumSize: const Size.fromHeight(46),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: BuzUpColors.blue),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: BuzUpColors.surfaceLight,
        elevation: 0,
        height: 64,
        indicatorColor: BuzUpColors.blue.withValues(alpha: 0.15),
        labelTextStyle: WidgetStatePropertyAll(TextStyle(
          fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.2)),
      ),
      dividerTheme: const DividerThemeData(color: BuzUpColors.border, thickness: 1, space: 1),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: const Color(0xFF15191E),
        contentTextStyle: const TextStyle(color: Colors.white),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  static ThemeData dark() {
    final base = ThemeData.dark(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: BuzUpColors.scaffoldDark,
      colorScheme: base.colorScheme.copyWith(
        primary: BuzUpColors.blueDark,
        onPrimary: const Color(0xFF06101F),
        secondary: BuzUpColors.orange,
        onSecondary: const Color(0xFF15191E),
        surface: BuzUpColors.surfaceDark,
        onSurface: Colors.white,
        error: BuzUpColors.danger,
        outline: BuzUpColors.borderDark,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: BuzUpColors.scaffoldDark,
        elevation: 0,
        scrolledUnderElevation: 0,
        foregroundColor: Colors.white,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 17,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.2,
        ),
      ),
      cardTheme: CardThemeData(
        color: BuzUpColors.surfaceDark,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: BuzUpColors.borderDark),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: BuzUpColors.surfaceDark,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        labelStyle: const TextStyle(color: BuzUpColors.mutedDark),
        hintStyle: const TextStyle(color: BuzUpColors.mutedDark),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: BuzUpColors.borderDark)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: BuzUpColors.borderDark)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: BuzUpColors.blueDark, width: 2)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: BuzUpColors.blueDark,
          foregroundColor: const Color(0xFF06101F),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          minimumSize: const Size.fromHeight(50),
          textStyle: const TextStyle(fontWeight: FontWeight.w800, letterSpacing: 0.3),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: Colors.white,
          side: const BorderSide(color: BuzUpColors.borderDark),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          minimumSize: const Size.fromHeight(46),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: BuzUpColors.blueDark),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: BuzUpColors.surfaceDark,
        elevation: 0,
        height: 64,
        indicatorColor: BuzUpColors.blueDark.withValues(alpha: 0.20),
        labelTextStyle: const WidgetStatePropertyAll(TextStyle(
          fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.2, color: Colors.white)),
      ),
      dividerTheme: const DividerThemeData(color: BuzUpColors.borderDark, thickness: 1, space: 1),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: BuzUpColors.surfaceDark,
        contentTextStyle: const TextStyle(color: Colors.white),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }
}
