import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';

/// Lightweight logger tagged "BuzUpMobile" (visible in Android logcat and
/// macOS/iOS Console as a unified subsystem) plus a "[BUZUP_MOBILE]" prefix
/// in stdout so it shows up under `flutter run`.
class Log {
  Log._();

  static const _name = 'BuzUpMobile';
  static const _tag = 'BUZUP_MOBILE';

  static void debug(String message, {Object? data}) =>
      _emit(level: 500, severity: 'DEBUG', message: message, data: data);

  static void info(String message, {Object? data}) =>
      _emit(level: 800, severity: 'INFO', message: message, data: data);

  static void warn(String message, {Object? data, Object? error, StackTrace? stack}) =>
      _emit(level: 900, severity: 'WARN', message: message, data: data, error: error, stack: stack);

  static void error(String message, {Object? data, Object? error, StackTrace? stack}) =>
      _emit(level: 1000, severity: 'ERROR', message: message, data: data, error: error, stack: stack);

  static void _emit({
    required int level,
    required String severity,
    required String message,
    Object? data,
    Object? error,
    StackTrace? stack,
  }) {
    final suffix = data != null ? ' | $data' : '';
    final formatted = '[$_tag][$severity] $message$suffix';
    developer.log(formatted, name: _name, level: level, error: error, stackTrace: stack);
    if (kDebugMode) debugPrint(formatted);
  }
}
