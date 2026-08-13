import 'package:flutter/material.dart';
import '../core/api/api_client.dart';
import '../models/user_model.dart';

class VolunteerProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  List<UserModel> _availableVolunteers = [];
  bool _isLoading = false;

  List<UserModel> get availableVolunteers => _availableVolunteers;
  bool get isLoading => _isLoading;

  Future<void> fetchAvailableVolunteers() async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/volunteers/available');
      _availableVolunteers = (response.data as List).map((j) => UserModel.fromJson(j)).toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> assignVolunteer({required int donationId, required int volunteerId}) async {
    try {
      await _apiClient.dio.post('/volunteers/assignments', queryParameters: {
        'donation_id': donationId,
        'volunteer_id': volunteerId,
      });
      return true;
    } catch (e) {
      return false;
    }
  }
}
