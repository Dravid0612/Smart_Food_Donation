import 'package:flutter/material.dart';
import '../core/api/api_client.dart';
import '../models/reward_model.dart';

class RewardProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  RewardModel? _reward;
  bool _isLoading = false;

  RewardModel? get reward => _reward;
  bool get isLoading => _isLoading;

  Future<void> fetchRewardDetails() async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/rewards/me');
      _reward = RewardModel.fromJson(response.data);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }
}
