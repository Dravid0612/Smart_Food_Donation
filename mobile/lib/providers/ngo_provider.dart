import 'package:flutter/material.dart';
import '../core/api/api_client.dart';
import '../models/ngo_model.dart';

class NgoProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  List<NgoModel> _ngos = [];
  NgoModel? _myNgo;
  bool _isLoading = false;

  List<NgoModel> get ngos => _ngos;
  NgoModel? get myNgo => _myNgo;
  bool get isVerified => _myNgo?.isVerified ?? false;
  bool get isLoading => _isLoading;

  bool _isTesting = false;

  void setMyNgoForTesting(NgoModel? ngo) {
    _myNgo = ngo;
    _isTesting = true;
    notifyListeners();
  }

  Future<void> fetchMyNgo() async {
    if (_isTesting) return;
    try {
      final response = await _apiClient.dio.get('/ngos/me');
      _myNgo = NgoModel.fromJson(response.data);
      notifyListeners();
    } catch (_) {}
  }

  Future<void> fetchNgos() async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/ngos');
      _ngos = (response.data as List).map((json) => NgoModel.fromJson(json)).toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> verifyNgo(int ngoId) async {
    try {
      await _apiClient.dio.post('/ngos/$ngoId/verify');
      await fetchMyNgo();
      await fetchNgos();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> updateNgoCapacity(int ngoId, int capacity, bool isAvailable) async {
    try {
      await _apiClient.dio.put('/ngos/$ngoId', data: {
        'capacity': capacity,
        'is_available': isAvailable,
      });
      await fetchMyNgo();
      await fetchNgos();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> updateOperatingHours(int ngoId, Map<String, dynamic> schedule) async {
    try {
      await _apiClient.dio.put('/ngos/$ngoId/operating-hours', data: {
        'operating_hours': schedule,
      });
      await fetchMyNgo();
      await fetchNgos();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> updateDemands(int ngoId, Map<String, dynamic> demands) async {
    try {
      await _apiClient.dio.put('/ngos/$ngoId/demands', data: {
        'demand_requirements': demands,
      });
      await fetchMyNgo();
      await fetchNgos();
      return true;
    } catch (e) {
      return false;
    }
  }
}

