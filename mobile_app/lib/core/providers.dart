import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';
import 'logger.dart';
import 'passenger_api.dart';
import 'storage.dart';

final secureStoreProvider = Provider<SecureStore>((ref) => SecureStore());

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(secureStoreProvider));
});

final passengerApiProvider = Provider<PassengerApi>((ref) {
  return PassengerApi(ref.watch(apiClientProvider));
});

final meProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  return ref.watch(passengerApiProvider).me();
});

final transactionsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  return ref.watch(passengerApiProvider).transactions(limit: 50);
});

const _kThemeKey = 'buzup.themeMode';
const _kBalanceVisibleKey = 'buzup.balanceVisible';
const _kLocaleKey = 'buzup.locale';

class ThemeController extends StateNotifier<ThemeMode> {
  ThemeController() : super(ThemeMode.system) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kThemeKey);
    switch (raw) {
      case 'light': state = ThemeMode.light; break;
      case 'dark': state = ThemeMode.dark; break;
      default: state = ThemeMode.system;
    }
  }

  Future<void> set(ThemeMode mode) async {
    state = mode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kThemeKey, mode.name);
    Log.info('theme.set $mode');
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

final themeControllerProvider = StateNotifierProvider<ThemeController, ThemeMode>((ref) {
  return ThemeController();
});

class BalanceVisibilityController extends StateNotifier<bool> {
  BalanceVisibilityController() : super(false) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    state = prefs.getBool(_kBalanceVisibleKey) ?? false;
  }

  Future<void> toggle() async {
    state = !state;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kBalanceVisibleKey, state);
  }
}

final balanceVisibleProvider = StateNotifierProvider<BalanceVisibilityController, bool>((ref) {
  return BalanceVisibilityController();
});

class LocaleController extends StateNotifier<Locale> {
  LocaleController() : super(const Locale('pt')) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kLocaleKey);
    if (raw == 'en' || raw == 'pt') {
      state = Locale(raw!);
    }
  }

  Future<void> set(String code) async {
    state = Locale(code);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kLocaleKey, code);
    Log.info('locale.set $code');
  }
}

final localeControllerProvider = StateNotifierProvider<LocaleController, Locale>((ref) {
  return LocaleController();
});
