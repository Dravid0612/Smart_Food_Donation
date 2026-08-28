import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../constants/app_constants.dart';

class SecureStorageService {
  static final SecureStorageService _instance = SecureStorageService._internal();
  factory SecureStorageService() => _instance;
  SecureStorageService._internal();

  final _storage = const FlutterSecureStorage();

  Future<void> saveToken(String token) async {
    await _storage.write(key: AppConstants.keyAuthToken, value: token);
  }

  Future<String?> getToken() async {
    return await _storage.read(key: AppConstants.keyAuthToken);
  }

  Future<void> saveRefreshToken(String refreshToken) async {
    await _storage.write(key: AppConstants.keyRefreshToken, value: refreshToken);
  }

  Future<String?> getRefreshToken() async {
    return await _storage.read(key: AppConstants.keyRefreshToken);
  }

  Future<void> deleteRefreshToken() async {
    await _storage.delete(key: AppConstants.keyRefreshToken);
  }

  Future<void> saveUserData(String userDataJson) async {
    await _storage.write(key: AppConstants.keyUserData, value: userDataJson);
  }

  Future<String?> getUserData() async {
    return await _storage.read(key: AppConstants.keyUserData);
  }

  Future<void> clearAll() async {
    await _storage.deleteAll();
  }
}
