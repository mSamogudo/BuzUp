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

  Future<void> saveDeviceSerial(String serial) => _storage.write(key: _kDeviceSerial, value: serial);
  Future<String?> getDeviceSerial() => _storage.read(key: _kDeviceSerial);

  Future<void> clearAll() async {
    await _storage.deleteAll();
  }
}
