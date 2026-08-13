import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../core/storage/secure_storage.dart';
import '../models/user_model.dart';

class AuthProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  final SecureStorageService _storage = SecureStorageService();

  UserModel? _currentUser;
  bool _isLoading = false;
  String? _errorMessage;

  UserModel? get currentUser => _currentUser;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _currentUser != null;

  Future<bool> checkAuthStatus() async {
    _isLoading = true;
    notifyListeners();
    try {
      final token = await _storage.getToken();
      if (token == null || token.isEmpty) {
        _currentUser = null;
        _isLoading = false;
        notifyListeners();
        return false;
      }

      final response = await _apiClient.dio.get('/auth/me');
      _currentUser = UserModel.fromJson(response.data);
      await _storage.saveUserData(jsonEncode(_currentUser!.toJson()));
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _currentUser = null;
      await _storage.clearAll();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.post('/auth/login', data: {
        'email': email,
        'password': password,
      });

      final String token = response.data['access_token'];
      await _storage.saveToken(token);

      // Fetch user details
      final userResponse = await _apiClient.dio.get('/auth/me');
      _currentUser = UserModel.fromJson(userResponse.data);
      await _storage.saveUserData(jsonEncode(_currentUser!.toJson()));

      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _errorMessage = e.error?.toString() ?? 'Invalid credentials';
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'An error occurred during login.';
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
    int? capacity,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/auth/register', data: {
        'name': name,
        'email': email,
        'password': password,
        'phone': phone,
        'role': role.toLowerCase(),
        'address': address,
        'organization_name': organizationName,
        'capacity': capacity,
      });

      // Auto login after registration
      return await login(email, password);
    } on DioException catch (e) {
      _errorMessage = e.error?.toString() ?? 'Registration failed.';
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'Registration failed. Please try again.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    _currentUser = null;
    await _storage.clearAll();
    notifyListeners();
  }
}
