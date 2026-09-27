import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../core/storage/secure_storage.dart';
import '../models/user_model.dart';

enum AuthStatus {
  unauthenticated,
  authenticating,
  authenticated,
  sessionExpired,
}

class AuthProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  final SecureStorageService _storage = SecureStorageService();

  UserModel? _currentUser;
  AuthStatus _status = AuthStatus.unauthenticated;
  bool _isLoading = false;
  String? _errorMessage;

  AuthProvider() {
    _apiClient.onSessionExpired = () {
      _currentUser = null;
      _status = AuthStatus.sessionExpired;
      _errorMessage = 'Your session has expired. Please log in again.';
      notifyListeners();
    };
  }

  UserModel? get currentUser => _currentUser;
  UserModel? get user => _currentUser;
  AuthStatus get status => _status;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _status == AuthStatus.authenticated && _currentUser != null;
  String get userRole => _currentUser?.role.toLowerCase() ?? 'donor';

  Future<void> refreshUserProfile() async {
    await checkAuthStatus();
  }

  Future<bool> checkAuthStatus() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final token = await _storage.getToken();
      if (token == null || token.isEmpty) {
        _currentUser = null;
        _status = AuthStatus.unauthenticated;
        _isLoading = false;
        notifyListeners();
        return false;
      }

      final response = await _apiClient.dio.get('/auth/me');
      _currentUser = UserModel.fromJson(response.data);
      _status = AuthStatus.authenticated;
      await _storage.saveUserData(jsonEncode(_currentUser!.toJson()));
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _currentUser = null;
      _status = AuthStatus.unauthenticated;
      await _storage.clearAll();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> login(String emailOrPhone, String password) async {
    _isLoading = true;
    _status = AuthStatus.authenticating;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.post('/auth/login', data: {
        'email': emailOrPhone.trim(),
        'password': password,
      });

      final String token = response.data['access_token'];
      final String? refreshToken = response.data['refresh_token'];
      await _storage.saveToken(token);
      if (refreshToken != null && refreshToken.isNotEmpty) {
        await _storage.saveRefreshToken(refreshToken);
      }

      // Fetch user details from /auth/me
      final userResponse = await _apiClient.dio.get('/auth/me');
      _currentUser = UserModel.fromJson(userResponse.data);
      _status = AuthStatus.authenticated;
      await _storage.saveUserData(jsonEncode(_currentUser!.toJson()));

      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _errorMessage = e.error?.toString() ?? 'Invalid credentials.';
      _status = AuthStatus.unauthenticated;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'Unable to connect to the server. Please check your internet connection.';
      _status = AuthStatus.unauthenticated;
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> register({
    required String name,
    required String email,
    required String password,
    String? phone,
    required String role,
    String? address,
    String? organizationName,
    String? description,
    int? capacity,
    String? vehicleType,
    int? carryingCapacity,
  }) async {
    _isLoading = true;
    _status = AuthStatus.authenticating;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/auth/register', data: {
        'name': name.trim(),
        'email': email.trim(),
        'password': password,
        'phone': phone?.trim(),
        'role': role.toLowerCase().trim(),
        'address': address?.trim(),
        'organization_name': organizationName?.trim(),
        'description': description?.trim(),
        'capacity': capacity ?? 100,
        'vehicle_type': vehicleType ?? 'bike',
        'carrying_capacity': carryingCapacity ?? 50,
      });

      // Auto login after successful registration
      return await login(email, password);
    } on DioException catch (e) {
      _errorMessage = e.error?.toString() ?? 'Registration failed.';
      _status = AuthStatus.unauthenticated;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'Registration failed. Please verify your details.';
      _status = AuthStatus.unauthenticated;
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    try {
      // Notify backend to revoke refresh token hash
      await _apiClient.dio.post('/auth/logout');
    } catch (_) {
      // Continue client-side teardown even if offline
    }
    _currentUser = null;
    _status = AuthStatus.unauthenticated;
    _errorMessage = null;
    await _storage.clearAll();
    notifyListeners();
  }

  Future<void> setSessionFromExternal(String accessToken, Map<String, dynamic> userData) async {
    await _storage.saveToken(accessToken);
    _currentUser = UserModel.fromJson(userData);
    _status = AuthStatus.authenticated;
    await _storage.saveUserData(jsonEncode(_currentUser!.toJson()));
    notifyListeners();
  }

  void setCurrentUserForTesting(UserModel user) {
    _currentUser = user;
    _status = AuthStatus.authenticated;
    notifyListeners();
  }
}
