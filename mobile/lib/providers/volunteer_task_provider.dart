import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../models/donation_model.dart';

/// Volunteer-specific provider. Only fetches and manages the
/// current volunteer's own assigned tasks, separate from the
/// general DonationProvider used by donors/NGOs.
class VolunteerTaskProvider with ChangeNotifier {
  final ApiClient _apiClient = ApiClient();

  List<DonationModel> _assignedTasks = [];
  DonationModel? _activeTask;
  bool _isLoading = false;
  String? _errorMessage;
  bool _isAvailable = true;

  List<DonationModel> get assignedTasks => _assignedTasks;
  DonationModel? get activeTask => _activeTask;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isAvailable => _isAvailable;

  int get completedCount => _assignedTasks.where((d) => d.status == 'delivered' || d.status == 'completed').length;
  int get pendingCount => _assignedTasks.where((d) => ['volunteer_assigned', 'collected'].contains(d.status)).length;
  int get totalMealsTransported => _assignedTasks
      .where((d) => d.status == 'delivered' || d.status == 'completed')
      .fold<int>(0, (sum, d) => sum + d.quantity.toInt());

  void setAvailability(bool available) {
    _isAvailable = available;
    notifyListeners();
    // In production: call API to update volunteer availability status
    // _apiClient.dio.put('/volunteers/availability', data: {'is_available': available});
  }

  Future<void> fetchMyTasks() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      // Fetches only donations assigned to the current volunteer
      final response = await _apiClient.dio.get('/volunteers/my-tasks');
      _assignedTasks = (response.data as List)
          .map((json) => DonationModel.fromJson(json))
          .toList();
      _isLoading = false;
      notifyListeners();
    } on DioException catch (e) {
      _errorMessage = e.error?.toString() ?? 'Failed to load tasks.';
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = 'Error loading tasks.';
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<DonationModel?> fetchTaskDetail(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId');
      _activeTask = DonationModel.fromJson(response.data);
      notifyListeners();
      return _activeTask;
    } catch (_) {
      return null;
    }
  }

  Future<bool> acceptPickupRequest(int donationId) async {
    try {
      await _apiClient.dio.post('/volunteers/assignments', queryParameters: {
        'donation_id': donationId,
      });
      await fetchMyTasks();
      return true;
    } catch (e) {
      _errorMessage = 'Failed to accept pickup request.';
      notifyListeners();
      return false;
    }
  }

  Future<bool> rejectPickupRequest(int donationId) async {
    try {
      await _apiClient.dio.post('/donations/$donationId/reject');
      await fetchMyTasks();
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Verifies pickup OTP (client-side demo validation).
  /// In production this would call a backend OTP validation endpoint.
  bool verifyPickupOtp(int donationId, String enteredOtp) {
    // Demo: OTP is generated deterministically from donationId
    // (Same logic as in DonationDetailScreen)
    final rng = Random(donationId * 7919);
    final expectedOtp = (1000 + rng.nextInt(8999)).toString();
    return enteredOtp == expectedOtp;
  }

  Future<bool> markCollected(int donationId) async {
    try {
      await _apiClient.dio.post('/donations/$donationId/collect');
      await fetchMyTasks();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> markDelivered(int donationId) async {
    try {
      await _apiClient.dio.post('/donations/$donationId/deliver');
      await fetchMyTasks();
      return true;
    } catch (_) {
      return false;
    }
  }
}
