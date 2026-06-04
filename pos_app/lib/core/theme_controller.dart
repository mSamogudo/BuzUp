import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Theme mode (system/light/dark) persisted in SharedPreferences.
class ThemeController extends StateNotifier<ThemeMode> {
  ThemeController() : super(ThemeMode.system) {
    _load();
  }

  static const _key = 'buzup.theme_mode';

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_key);
    switch (saved) {
      case 'light':
        state = ThemeMode.light;
        break;
      case 'dark':
        state = ThemeMode.dark;
        break;
      default:
        state = ThemeMode.system;
    }
  }

  Future<void> set(ThemeMode mode) async {
    state = mode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, switch (mode) {
      ThemeMode.light => 'light',
      ThemeMode.dark => 'dark',
      ThemeMode.system => 'system',
    });
  }

  Future<void> toggle() async {
    final next = switch (state) {
      ThemeMode.light => ThemeMode.dark,
      ThemeMode.dark => ThemeMode.system,
      ThemeMode.system => ThemeMode.light,
    };
    await set(next);
  }
}

final themeControllerProvider = StateNotifierProvider<ThemeController, ThemeMode>(
  (ref) => ThemeController(),
);
