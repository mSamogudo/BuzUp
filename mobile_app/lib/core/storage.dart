import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure JWT storage backed by Android Keystore / iOS Keychain.
class SecureStore {
  static const _opts = AndroidOptions(encryptedSharedPreferences: true);
  static const _storage = FlutterSecureStorage(aOptions: _opts);
  static const _kAccess = 'buzup.passenger.access';
  static const _kRefresh = 'buzup.passenger.refresh';
  static const _kPhone = 'buzup.passenger.phone';

  Future<void> saveTokens({required String access, required String refresh}) async {
    await _storage.write(key: _kAccess, value: access);
    await _storage.write(key: _kRefresh, value: refresh);
  }

  Future<String?> getAccess() => _storage.read(key: _kAccess);
  Future<String?> getRefresh() => _storage.read(key: _kRefresh);

  Future<void> savePhone(String phone) => _storage.write(key: _kPhone, value: phone);
  Future<String?> getPhone() => _storage.read(key: _kPhone);

  Future<void> clearAll() => _storage.deleteAll();
}
