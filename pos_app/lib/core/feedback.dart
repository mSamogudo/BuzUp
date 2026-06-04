import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/services.dart';

/// Loud audible feedback for validations / sales / errors.
///
/// Uses an embedded WAV (raw PCM) bundled in `assets/sounds/`.
/// On SUNMI/Urovo this plays through the built-in speaker at full volume.
class AppFeedback {
  static final AudioPlayer _okPlayer = AudioPlayer()..setReleaseMode(ReleaseMode.stop);
  static final AudioPlayer _errPlayer = AudioPlayer()..setReleaseMode(ReleaseMode.stop);
  static final AudioPlayer _softPlayer = AudioPlayer()..setReleaseMode(ReleaseMode.stop);

  static Future<void> _playAsset(AudioPlayer p, String asset) async {
    try {
      await p.setVolume(1.0);
      await p.stop();
      await p.play(AssetSource(asset), volume: 1.0);
    } catch (_) {
      // Fallback to system sound if asset playback fails
      await SystemSound.play(SystemSoundType.click);
    }
  }

  static Future<void> success() async {
    HapticFeedback.lightImpact();
    await _playAsset(_okPlayer, 'sounds/beep_ok.wav');
  }

  static Future<void> error() async {
    HapticFeedback.heavyImpact();
    await _playAsset(_errPlayer, 'sounds/beep_err.wav');
  }

  static Future<void> click() async {
    HapticFeedback.selectionClick();
    await SystemSound.play(SystemSoundType.click);
  }

  /// Gentle short tone (~1.1 kHz, 90 ms, low volume). Used when reading a
  /// physical card so the operator hears a discreet confirmation, not the
  /// loud success/error beeps reserved for validations.
  static Future<void> softBeep() async {
    HapticFeedback.selectionClick();
    try {
      await _softPlayer.setVolume(0.6);
      await _softPlayer.stop();
      await _softPlayer.play(AssetSource('sounds/beep_soft.wav'), volume: 0.6);
    } catch (_) {/* swallow */}
  }
}
