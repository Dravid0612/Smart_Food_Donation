import 'package:flutter/material.dart';
import '../core/api/api_client.dart';
import '../models/user_model.dart';
import '../models/ngo_model.dart';
import '../models/donation_model.dart';

class AdminProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();

  Map<String, dynamic>? _statistics;
  List<UserModel> _allUsers = [];
  List<NgoModel> _allNgos = [];
  List<DonationModel> _allDonations = [];
  bool _isLoading = false;

  Map<String, dynamic>? get statistics => _statistics;
  List<UserModel> get allUsers => _allUsers;
  List<NgoModel> get allNgos => _allNgos;
  List<DonationModel> get allDonations => _allDonations;
  bool get isLoading => _isLoading;

  Future<void> fetchAdminStatistics() async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/admin/statistics');
      _statistics = response.data;
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchAllUsers() async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/admin/users');
      _allUsers = (response.data as List).map((j) => UserModel.fromJson(j)).toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchAllNgos() async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/admin/ngos');
      _allNgos = (response.data as List).map((j) => NgoModel.fromJson(j)).toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchAllDonations() async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/admin/donations');
      _allDonations = (response.data as List).map((j) => DonationModel.fromJson(j)).toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> toggleUserActive(int userId) async {
    try {
      await _apiClient.dio.put('/admin/users/$userId/toggle-active');
      await fetchAllUsers();
      return true;
    } catch (e) {
      return false;
    }
  }
}
