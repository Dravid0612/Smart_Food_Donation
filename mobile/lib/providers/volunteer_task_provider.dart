import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../models/donation_model.dart';

/// Volunteer-specific provider for tasks, backend OTP/QR validation, failure reporting, and profile management.
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
  }

  Future<void> fetchMyTasks() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/donations');
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
    _errorMessage = null;
    try {
      await _apiClient.dio.post('/volunteers/assignments', queryParameters: {
        'donation_id': donationId,
      });
      await fetchMyTasks();
      return true;
    } on DioException catch (e) {
      if (e.response?.data != null && e.response?.data is Map && e.response?.data['detail'] != null) {
        _errorMessage = e.response?.data['detail'].toString();
      } else {
        _errorMessage = e.message ?? 'Failed to accept pickup request.';
      }
      notifyListeners();
      return false;
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

  /// Backend-verified pickup confirmation with 6-digit OTP
  Future<bool> verifyPickupOtp(int donationId, String enteredOtp) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/volunteers/verify-otp', data: {
        'donation_id': donationId,
        'otp': enteredOtp,
      });
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _errorMessage = e.error?.toString() ?? 'Invalid OTP code entered.';
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'Verification error.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Backend-verified pickup confirmation with QR code token
  Future<bool> verifyPickupQr(int donationId, String qrToken) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/volunteers/verify-qr', data: {
        'donation_id': donationId,
        'qr_token': qrToken,
      });
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = 'Invalid QR code.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Reports pickup/delivery failure to backend with structured reasons
  Future<bool> reportFailure({
    required int donationId,
    required String failureType,
    required String reason,
    String? remarks,
  }) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post(
        '/volunteers/report-failure',
        queryParameters: {'donation_id': donationId},
        data: {
          'failure_type': failureType,
          'reason': reason,
          'remarks': remarks,
        },
      );
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> startPickup(int donationId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final myTasks = _assignedTasks.where((t) => t.id == donationId).toList();
      if (myTasks.isNotEmpty) {
        // If we have local assignment ID, call directly
      }
      await _apiClient.dio.put('/volunteers/assignments/0', data: 'en_route', queryParameters: {'status_update': 'en_route', 'donation_id': donationId}).catchError((_) async {
        return await _apiClient.dio.post('/volunteers/assignments/$donationId/start-pickup');
      });
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (_) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> markArrived(int donationId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/volunteers/assignments/$donationId/arrived').catchError((_) async {
        return await _apiClient.dio.put('/volunteers/assignments/0', data: 'arrived', queryParameters: {'status_update': 'arrived', 'donation_id': donationId});
      });
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (_) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
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

