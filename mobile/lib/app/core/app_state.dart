import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api_service.dart';

class AuthProvider with ChangeNotifier {
  AuthProvider({required this.apiService});

  final ApiService apiService;
  bool isAuthenticated = false;
  bool isLoading = false;
  String? token;
  String? role;
  String? name;
  String? email;
  String? errorMessage;

  Future<void> restoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    token = prefs.getString('token');
    role = prefs.getString('role');
    name = prefs.getString('name');
    email = prefs.getString('email');
    isAuthenticated = token != null;
    notifyListeners();
  }

  Future<void> login(String emailInput, String password) async {
    isLoading = true;
    errorMessage = null;
    notifyListeners();
    try {
      final response = await apiService.login(emailInput, password);
      if (response['access_token'] != null) {
      token = response['access_token'];
      role = response['role'];
      name = response['name'];
      email = emailInput;
      isAuthenticated = true;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('token', token!);
      await prefs.setString('role', role ?? 'donor');
      await prefs.setString('name', name ?? 'User');
      await prefs.setString('email', email ?? emailInput);
      }
    } catch (error) {
      errorMessage = error.toString();
    }
    isLoading = false;
    notifyListeners();
  }

  Future<void> register(String nameInput, String emailInput, String password, String roleInput) async {
    isLoading = true;
    errorMessage = null;
    notifyListeners();
    try {
      final response = await apiService.register(nameInput, emailInput, password, roleInput);
      if (response['access_token'] != null) {
      token = response['access_token'];
      role = roleInput;
      name = nameInput;
      email = emailInput;
      isAuthenticated = true;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('token', token!);
      await prefs.setString('role', role!);
      await prefs.setString('name', name!);
      await prefs.setString('email', email!);
      }
    } catch (error) {
      errorMessage = error.toString();
    }
    isLoading = false;
    notifyListeners();
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    token = null;
    role = null;
    name = null;
    email = null;
    isAuthenticated = false;
    notifyListeners();
  }
}

class DonationProvider with ChangeNotifier {
  DonationProvider({required this.apiService});

  final ApiService apiService;
  bool isLoading = false;
  List<dynamic> donations = [];
  List<dynamic> availableDonations = [];
  String? errorMessage;

  Future<void> loadDonations(String token) async {
    isLoading = true;
    notifyListeners();
    try {
      donations = await apiService.fetchDonations(token);
      errorMessage = null;
    } catch (error) {
      donations = [];
      errorMessage = error.toString();
    }
    isLoading = false;
    notifyListeners();
  }

  Future<void> createDonation(String token, Map<String, dynamic> donation) async {
    isLoading = true;
    notifyListeners();
    try {
      await apiService.createDonation(token, donation);
      await loadDonations(token);
    } catch (error) {
      errorMessage = error.toString();
      isLoading = false;
      notifyListeners();
      rethrow;
    }
  }

  Future<void> loadAvailableDonations(String token) async {
    isLoading = true;
    notifyListeners();
    try {
      availableDonations = await apiService.fetchAvailableDonations(token);
      errorMessage = null;
    } catch (error) {
      availableDonations = [];
      errorMessage = error.toString();
    }
    isLoading = false;
    notifyListeners();
  }

  Future<void> updateDonationStatus(String token, int id, String status) async {
    await apiService.updateDonationStatus(token, id, status);
    await loadAvailableDonations(token);
  }
}
