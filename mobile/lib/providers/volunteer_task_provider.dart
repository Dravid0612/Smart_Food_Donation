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
  final Map<int, int> _donationToAssignmentMap = {};

  bool _isTesting = false;

  List<DonationModel> get assignedTasks => _assignedTasks;
  DonationModel? get activeTask => _activeTask;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isAvailable => _isAvailable;
  int? getAssignmentId(int donationId) => _donationToAssignmentMap[donationId];

  int get completedCount => _assignedTasks.where((d) => d.status == 'delivered' || d.status == 'completed').length;
  int get pendingCount => _assignedTasks.where((d) => ['volunteer_assigned', 'accepted', 'en_route', 'arrived', 'collected', 'in_transit'].contains(d.status)).length;
  int get totalMealsTransported => _assignedTasks
      .where((d) => d.status == 'delivered' || d.status == 'completed')
      .fold<int>(0, (sum, d) => sum + d.quantity.toInt());

  Future<void> setAvailability(bool available) async {
    _isAvailable = available;
    notifyListeners();
    if (_isTesting) return;
    try {
      await _apiClient.dio.put('/volunteers/profile', data: {
        'is_active': available,
      });
      await fetchMyTasks();
    } catch (_) {}
  }

  @visibleForTesting
  void setTasksForTesting(List<DonationModel> tasks) {
    _isTesting = true;
    _assignedTasks = tasks;
    notifyListeners();
  }

  @visibleForTesting
  void setActiveTaskForTesting(DonationModel? task) {
    _isTesting = true;
    _activeTask = task;
    notifyListeners();
  }

  @visibleForTesting
  void setAvailabilityForTesting(bool available) {
    _isTesting = true;
    _isAvailable = available;
    notifyListeners();
  }

  @visibleForTesting
  void setAssignmentIdForTesting(int donationId, int assignmentId) {
    _isTesting = true;
    if (assignmentId > 0) {
      _donationToAssignmentMap[donationId] = assignmentId;
    }
    notifyListeners();
  }

  Future<void> fetchMyTasks() async {
    if (_isTesting) return;
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/donations');
      _assignedTasks = (response.data as List)
          .map((json) => DonationModel.fromJson(json))
          .toList();
      for (final t in _assignedTasks) {
        if (t.assignmentId != null && t.assignmentId! > 0) {
          _donationToAssignmentMap[t.id] = t.assignmentId!;
        }
      }
      _isLoading = false;
      notifyListeners();
    } on DioException catch (e) {
      if (e.response?.data != null && e.response?.data is Map && e.response?.data['detail'] != null) {
        _errorMessage = e.response?.data['detail'].toString();
      } else {
        _errorMessage = e.message ?? 'Failed to load tasks.';
      }
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = 'Error loading tasks.';
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<DonationModel?> fetchTaskDetail(int donationId) async {
    if (_isTesting) return _activeTask;
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
      final response = await _apiClient.dio.post('/volunteers/assignments', queryParameters: {
        'donation_id': donationId,
      });
      if (response.data != null && response.data is Map && response.data['id'] != null) {
        final assignId = response.data['id'] as int;
        if (assignId > 0) {
          _donationToAssignmentMap[donationId] = assignId;
        }
      }
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

  Future<bool> rejectPickupRequest(int donationId, {String? reason}) async {
    try {
      final assignId = _donationToAssignmentMap[donationId];
      if (assignId != null && assignId > 0) {
        await _apiClient.dio.post(
          '/volunteers/assignments/$assignId/reject',
          queryParameters: {
            if (reason != null && reason.isNotEmpty) 'reason': reason,
          },
        );
      } else {
        await _apiClient.dio.post(
          '/donations/$donationId/reject',
          queryParameters: {
            if (reason != null && reason.isNotEmpty) 'reason': reason,
          },
        );
      }
      await fetchMyTasks();
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Backend-verified pickup confirmation with 6-digit OTP
  Future<bool> verifyPickupOtp(int donationId, String enteredOtp) async {
    if (_isTesting) {
      _isLoading = false;
      notifyListeners();
      return true;
    }
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/volunteers/verify-otp', data: {
        'donation_id': donationId,
        'otp': enteredOtp.trim(),
      });
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      if (e.response?.data != null && e.response?.data is Map && e.response?.data['detail'] != null) {
        _errorMessage = e.response?.data['detail'].toString();
      } else {
        _errorMessage = e.message ?? 'Invalid OTP code entered.';
      }
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
    if (_isTesting) {
      _isLoading = false;
      notifyListeners();
      return true;
    }
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final assignId = _donationToAssignmentMap[donationId];
      if (assignId != null && assignId > 0) {
        await _apiClient.dio.post('/volunteers/assignments/$assignId/start-pickup');
      } else {
        await _apiClient.dio.post('/volunteers/donations/$donationId/start-pickup');
      }
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _errorMessage = e.response?.data?['detail']?.toString() ?? e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (_) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> markArrived(int donationId, {String method = 'gps', String? reason}) async {
    if (_isTesting) {
      _isLoading = false;
      notifyListeners();
      return true;
    }
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final assignId = _donationToAssignmentMap[donationId];
      final queryParams = <String, dynamic>{
        'method': method,
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      };

      if (assignId != null && assignId > 0) {
        await _apiClient.dio.post('/volunteers/assignments/$assignId/arrived', queryParameters: queryParams);
      } else {
        await _apiClient.dio.post('/volunteers/donations/$donationId/arrived', queryParameters: queryParams);
      }
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _errorMessage = e.response?.data?['detail']?.toString() ?? e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (_) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> startTransit(int donationId) async {
    if (_isTesting) {
      _isLoading = false;
      notifyListeners();
      return true;
    }
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/volunteers/donations/$donationId/in-transit');
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _errorMessage = e.response?.data?['detail']?.toString() ?? e.message;
      _isLoading = false;
      notifyListeners();
      return false;
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
    if (_isTesting) {
      _isLoading = false;
      notifyListeners();
      return true;
    }
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/deliver');
      await fetchTaskDetail(donationId);
      await fetchMyTasks();
      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _errorMessage = e.response?.data?['detail']?.toString() ?? e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (_) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Public preview for shareable rescue claim link
  Future<RescueClaimPreviewModel?> fetchClaimPreview(String token) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/volunteers/claims/$token');
      _isLoading = false;
      notifyListeners();
      return RescueClaimPreviewModel.fromJson(response.data);
    } on DioException catch (e) {
      _isLoading = false;
      if (e.response?.data != null && e.response?.data is Map && e.response?.data['detail'] != null) {
        _errorMessage = e.response?.data['detail'].toString();
      } else {
        _errorMessage = e.message ?? 'Invalid or expired claim link.';
      }
      notifyListeners();
      return null;
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'Failed to load rescue preview.';
      notifyListeners();
      return null;
    }
  }

  /// Frictionless first-time volunteer claim acceptance
  Future<RescueClaimAcceptResult?> acceptClaim({
    required String token,
    required String name,
    required String phone,
    String vehicleType = 'bike',
    int carryingCapacity = 50,
    double? currentLat,
    double? currentLon,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.post('/volunteers/claims/$token/accept', data: {
        'name': name.trim(),
        'phone': phone.trim(),
        'vehicle_type': vehicleType,
        'carrying_capacity': carryingCapacity,
        'current_lat': currentLat,
        'current_lon': currentLon,
      });
      final result = RescueClaimAcceptResult.fromJson(response.data);
      if (result.assignmentId > 0 && result.donationId > 0) {
        _donationToAssignmentMap[result.donationId] = result.assignmentId;
      }
      _isLoading = false;
      notifyListeners();
      return result;
    } on DioException catch (e) {
      _isLoading = false;
      if (e.response?.data != null && e.response?.data is Map && e.response?.data['detail'] != null) {
        _errorMessage = e.response?.data['detail'].toString();
      } else {
        _errorMessage = e.message ?? 'Failed to claim rescue.';
      }
      notifyListeners();
      return null;
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'Error claiming rescue.';
      notifyListeners();
      return null;
    }
  }

  /// Optional account upgrade after completing first rescue
  Future<bool> upgradeAccount({
    required String email,
    required String password,
    String preferredLanguage = 'en',
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/volunteers/upgrade-account', data: {
        'email': email.trim().toLowerCase(),
        'password': password,
        'preferred_language': preferredLanguage,
      });
      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _isLoading = false;
      if (e.response?.data != null && e.response?.data is Map && e.response?.data['detail'] != null) {
        _errorMessage = e.response?.data['detail'].toString();
      } else {
        _errorMessage = e.message ?? 'Failed to upgrade account.';
      }
      notifyListeners();
      return false;
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'Error upgrading account.';
      notifyListeners();
      return false;
    }
  }
}

