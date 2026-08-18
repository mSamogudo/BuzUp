import 'dart:convert';
import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure key-value storage for tokens and small bits of credentials.
class SecureStore {
  static const _opts = AndroidOptions(encryptedSharedPreferences: true);
  static const _storage = FlutterSecureStorage(aOptions: _opts);

  static const _kAccess = 'buzup.access_token';
  static const _kRefresh = 'buzup.refresh_token';
  static const _kAgentId = 'buzup.agent_id';
  static const _kAgentName = 'buzup.agent_name';
  static const _kDeviceSerial = 'buzup.device_serial';
  static const _kDriverId = 'buzup.driver_id';
  static const _kInstallId = 'buzup.install_id';

  Future<void> saveTokens({required String access, required String refresh}) async {
    await _storage.write(key: _kAccess, value: access);
    await _storage.write(key: _kRefresh, value: refresh);
  }

  Future<String?> getAccess() => _storage.read(key: _kAccess);
  Future<String?> getRefresh() => _storage.read(key: _kRefresh);

  Future<void> saveAgent({required int id, required String name}) async {
    await _storage.write(key: _kAgentId, value: id.toString());
    await _storage.write(key: _kAgentName, value: name);
  }

  Future<int?> getAgentId() async {
    final v = await _storage.read(key: _kAgentId);
    return v != null ? int.tryParse(v) : null;
  }

  Future<String?> getAgentName() => _storage.read(key: _kAgentName);

  Future<void> saveDriverId(int? id) async {
    if (id == null) {
      await _storage.delete(key: _kDriverId);
    } else {
      await _storage.write(key: _kDriverId, value: id.toString());
    }
  }

  Future<int?> getDriverId() async {
    final v = await _storage.read(key: _kDriverId);
    return v != null ? int.tryParse(v) : null;
  }

  Future<void> saveDeviceSerial(String serial) => _storage.write(key: _kDeviceSerial, value: serial);
  Future<String?> getDeviceSerial() => _storage.read(key: _kDeviceSerial);

  /// Identidade deste aparelho quando o Android nao da o numero de serie.
  ///
  /// Gerada uma vez e guardada para sempre. Ver [clearAll]: nao e uma
  /// credencial, e o equivalente ao numero gravado na carcaca do terminal.
  Future<String> installationId() async {
    final existente = await _storage.read(key: _kInstallId);
    if (existente != null && existente.isNotEmpty) return existente;
    final rnd = Random.secure();
    final bytes = List<int>.generate(16, (_) => rnd.nextInt(256));
    final novo = 'INS-${base64Url.encode(bytes).replaceAll('=', '')}';
    await _storage.write(key: _kInstallId, value: novo);
    return novo;
  }

  Future<void> clearAll() async {
    // O identificador do aparelho sobrevive: revogar o dispositivo tira-lhe a
    // sessao, nao a identidade. Se mudasse aqui, o mesmo terminal voltaria a
    // aparecer como um dispositivo novo a cada revogacao e o administrador
    // ficaria com uma lista de fantasmas para aprovar.
    final identidade = await _storage.read(key: _kInstallId);
    await _storage.deleteAll();
    if (identidade != null) {
      await _storage.write(key: _kInstallId, value: identidade);
    }
  }
}
