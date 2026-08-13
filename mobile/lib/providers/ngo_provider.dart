import 'package:flutter/material.dart';
import '../core/api/api_client.dart';
import '../models/ngo_model.dart';

class NgoProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  List<NgoModel> _ngos = [];
  bool _isLoading = false;

  List<NgoModel> get ngos => _ngos;
  bool get isLoading => _isLoading;

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
      await fetchNgos();
      return true;
    } catch (e) {
      return false;
    }
  }
}
