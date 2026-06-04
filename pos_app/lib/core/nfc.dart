import 'dart:async';

import 'package:flutter/services.dart';

/// Native NFC bridge backed by `MainActivity` Kotlin code.
///
/// Uses `NfcAdapter.enableReaderMode` with `FLAG_READER_SKIP_NDEF_CHECK` to
/// take exclusive ownership of the reader while a screen is visible. This
/// guarantees the OS never falls back to the system "New tag collected"
/// dispatcher, which would interrupt the agent's workflow.
class NfcCardReader {
  static const MethodChannel _channel = MethodChannel('buzup.nfc');
  static Future<void> Function(String uid)? _onUid;
  static bool _wired = false;

  static void _wire() {
    if (_wired) return;
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onTag') {
        final uid = (call.arguments as String?) ?? '';
        if (uid.isEmpty) return;
        final cb = _onUid;
        if (cb != null) {
          await cb(uid);
        }
      }
    });
    _wired = true;
  }

  /// Long-lived reader mode. Calls [onUid] for each card detected until
  /// [stop] is invoked.
  static Future<void> startStream(Future<void> Function(String uid) onUid) async {
    _wire();
    final ok = await _channel.invokeMethod<bool>('isAvailable') ?? false;
    if (!ok) {
      throw const NfcUnavailableException('Leitor NFC indisponivel neste dispositivo.');
    }
    _onUid = onUid;
    await _channel.invokeMethod('start');
  }

  /// Stop reader mode. Idempotent.
  static Future<void> stop() async {
    try {
      await _channel.invokeMethod('stop');
    } catch (_) {/* idempotent */}
    _onUid = null;
  }

  /// Convenience for single-shot reads. Starts a reader mode session and
  /// completes with the first UID, then stops.
  static Future<String> readOnce({Duration timeout = const Duration(seconds: 30)}) async {
    final completer = Completer<String>();
    await startStream((uid) async {
      if (!completer.isCompleted) completer.complete(uid);
      await stop();
    });
    return completer.future.timeout(timeout, onTimeout: () async {
      await stop();
      throw TimeoutException('Tempo esgotado a aguardar cartao.');
    });
  }
}

class NfcUnavailableException implements Exception {
  final String message;
  const NfcUnavailableException(this.message);
  @override
  String toString() => message;
}
