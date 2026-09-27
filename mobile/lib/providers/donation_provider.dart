import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../models/donation_model.dart';
import '../models/recommendation_model.dart';
import '../models/recurring_donation_model.dart';
import '../models/certificate_model.dart';
import '../models/rating_model.dart';
import '../models/donor_impact_model.dart';
import '../models/feedback_model.dart';
import '../models/performance_model.dart';

class DonationProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();

  List<DonationModel> _donations = [];
  DonationModel? _currentDetail;
  List<NgoRecommendationModel> _ngoRecommendations = [];
  List<VolunteerRecommendationModel> _volunteerRecommendations = [];
  List<DonorCustomFoodProfileModel> _myFoods = [];
  DonorImpactSummaryModel? _donorImpact;
  bool _isLoading = false;
  String? _errorMessage;

  List<DonationModel> get donations => _donations;
  DonationModel? get currentDetail => _currentDetail;
  List<NgoRecommendationModel> get ngoRecommendations => _ngoRecommendations;
  List<VolunteerRecommendationModel> get volunteerRecommendations => _volunteerRecommendations;
  List<DonorCustomFoodProfileModel> get myFoods => _myFoods;
  DonorImpactSummaryModel? get donorImpact => _donorImpact;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  /// Proactive Time-Critical Rescues (< 120m rescue window)
  List<DonationModel> get urgentDonations => _donations.where((d) {
        if (d.status.toLowerCase() != 'pending') return false;
        final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
        return urg == 'URGENT';
      }).toList();

  /// Critical Emergency Rescues (< 45m rescue window)
  List<DonationModel> get criticalDonations => _donations.where((d) {
        if (d.status.toLowerCase() != 'pending') return false;
        final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
        return urg == 'CRITICAL';
      }).toList();

  /// Fetches authoritative server dispatch status for a donation
  Future<Map<String, dynamic>?> fetchDispatchStatus(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/dispatch-status');
      return response.data as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  /// Triggers a proactive alert dispatch wave
  Future<bool> triggerProactiveDispatch(int donationId) async {
    try {
      await _apiClient.dio.post('/donations/$donationId/trigger-dispatch');
      await fetchDonations();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> fetchMyFoods() async {
    try {
      final response = await _apiClient.dio.get('/donations/my-foods');
      _myFoods = (response.data as List)
          .map((json) => DonorCustomFoodProfileModel.fromJson(json))
          .toList();
      notifyListeners();
    } catch (_) {}
  }

  Future<bool> addCustomFoodToLibrary({
    required String name,
    required String foodCategory,
    String? description,
    String? majorIngredients,
    String commonStorage = 'Room Temperature',
    String defaultUnit = 'Meals',
  }) async {
    try {
      await _apiClient.dio.post('/donations/my-foods', data: {
        'name': name,
        'food_category': foodCategory,
        'description': description,
        'major_ingredients': majorIngredients,
        'common_storage': commonStorage,
        'default_unit': defaultUnit,
      });
      await fetchMyFoods();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> deleteCustomFoodFromLibrary(int profileId) async {
    try {
      await _apiClient.dio.delete('/donations/my-foods/$profileId');
      await fetchMyFoods();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> fetchDonations({String? status, String? category, bool myDonationsOnly = false}) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final queryParams = <String, dynamic>{};
      if (status != null && status.isNotEmpty) queryParams['status'] = status;
      if (category != null && category.isNotEmpty) queryParams['category'] = category;
      if (myDonationsOnly) queryParams['my_donations_only'] = 'true';

      final response = await _apiClient.dio.get('/donations', queryParameters: queryParams);
      _donations = (response.data as List).map((json) => DonationModel.fromJson(json)).toList();
      _isLoading = false;
      notifyListeners();
    } on DioException catch (e) {
      _errorMessage = e.error?.toString() ?? 'Failed to load donations.';
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = 'An error occurred while fetching donations.';
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<DonationModel?> fetchDonationDetail(int donationId) async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/donations/$donationId');
      _currentDetail = DonationModel.fromJson(response.data);
      _isLoading = false;
      notifyListeners();
      return _currentDetail;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  Future<bool> createDonation({
    required String foodName,
    String? foodType,
    String foodSource = 'KNOWN',
    String? customFoodName,
    String? foodDescription,
    String? majorIngredients,
    required String foodCategory,
    required double quantity,
    required String quantityUnit,
    String? quantityUnitLabel,
    double? estimatedMeals,
    String ruleCoverage = 'HIGH',
    required DateTime preparationTime,
    required DateTime expiryTime,
    required String pickupAddress,
    String? description,
    double? latitude,
    double? longitude,
    String? imageUrl,
    String? storageMethod,
    double? storageDurationHours,
    bool storageContinuous = true,
    String? storageHistoryJson,
    String? packagingCondition,
    String previouslyServed = 'No',
    String exposureStatus = 'No',
    String handlingStatus = 'No',
    DateTime? pickupDeadline,
    String? aiFoodDetected,
    String? aiVisibleSpoilage,
    String? aiDiscoloration,
    String? aiPackagingIntact,
    String? aiVisualCondition,
    double? aiConfidenceScore,
    int? conditionScore,
    Map<String, dynamic>? safetyCheckAnswers,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations', data: {
        'food_name': foodName,
        'food_type': foodType ?? foodName,
        'food_source': foodSource,
        'custom_food_name': customFoodName,
        'food_description': foodDescription ?? description,
        'major_ingredients': majorIngredients,
        'food_category': foodCategory,
        'quantity': quantity,
        'quantity_unit': quantityUnit,
        'quantity_unit_label': quantityUnitLabel,
        'estimated_meals': estimatedMeals,
        'rule_coverage': ruleCoverage,
        'preparation_time': preparationTime.toUtc().toIso8601String(),
        'expiry_time': expiryTime.toUtc().toIso8601String(),
        'pickup_address': pickupAddress,
        'description': description,
        'latitude': latitude,
        'longitude': longitude,
        'image_url': imageUrl,
        'storage_method': storageMethod ?? 'Room Temperature',
        'storage_duration_hours': storageDurationHours ?? 2.0,
        'storage_continuous': storageContinuous,
        'storage_history_json': storageHistoryJson,
        'packaging_condition': packagingCondition ?? 'Covered',
        'previously_served': previouslyServed,
        'exposure_status': exposureStatus,
        'handling_status': handlingStatus,
        'pickup_deadline': (pickupDeadline ?? expiryTime).toUtc().toIso8601String(),
        'ai_food_detected': aiFoodDetected,
        'ai_visible_spoilage': aiVisibleSpoilage,
        'ai_discoloration': aiDiscoloration,
        'ai_packaging_intact': aiPackagingIntact,
        'ai_visual_condition': aiVisualCondition ?? 'GOOD',
        'ai_confidence_score': aiConfidenceScore ?? 0.88,
        'condition_score': conditionScore ?? 85,
        if (safetyCheckAnswers != null) 'safety_check_answers': safetyCheckAnswers,
      });

      await fetchDonations();
      await fetchMyFoods();
      _isLoading = false;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _errorMessage = e.error?.toString() ?? 'Failed to create donation.';
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'An error occurred while creating donation.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> cancelDonation(int donationId, String reason) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/cancel', data: {
        'reason': reason,
      });
      await fetchDonationDetail(donationId);
      await fetchDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> escalateDonation(int donationId) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/escalate');
      await fetchDonationDetail(donationId);
      await fetchDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> acceptDonation(int donationId, {String pickupMode = 'volunteer_dispatch'}) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/accept', data: {
        'pickup_mode': pickupMode,
      });
      await fetchDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> requestVolunteer(int donationId) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/request-volunteer');
      await fetchDonationDetail(donationId);
      await fetchDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> rejectDonation(int donationId) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/reject');
      await fetchDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> collectDonation(int donationId) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/collect');
      await fetchDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> deliverDonation(int donationId) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/deliver');
      await fetchDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> recordDistribution({
    required int donationId,
    required double distributedQuantity,
    double? receivedQuantity,
    double? remainingQuantity,
    int? beneficiariesServed,
    String? remarks,
  }) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/distribution', data: {
        'distributed_quantity': distributedQuantity,
        'received_quantity': receivedQuantity,
        'remaining_quantity': remainingQuantity,
        'beneficiaries_served': beneficiariesServed ?? distributedQuantity.toInt(),
        'remarks': remarks,
      });
      await fetchDonationDetail(donationId);
      await fetchDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  List<RecurringDonationModel> _recurringDonations = [];
  CSRImpactSummaryModel? _csrSummary;
  CertificateModel? _certificate;
  List<RatingModel> _ratings = [];

  List<RecurringDonationModel> get recurringDonations => _recurringDonations;
  CSRImpactSummaryModel? get csrSummary => _csrSummary;
  CertificateModel? get certificate => _certificate;
  List<RatingModel> get ratings => _ratings;

  Future<void> fetchNgoRecommendations(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/recommend-ngo');
      _ngoRecommendations = (response.data as List)
          .map((json) => NgoRecommendationModel.fromJson(json))
          .toList();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> fetchVolunteerRecommendations(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/recommend-volunteer');
      _volunteerRecommendations = (response.data as List)
          .map((json) => VolunteerRecommendationModel.fromJson(json))
          .toList();
      notifyListeners();
    } catch (_) {}
  }

  // ── Recurring Donations ──────────────────────────────────────────────────
  Future<void> fetchRecurringDonations() async {
    try {
      final response = await _apiClient.dio.get('/donations/recurring/list');
      _recurringDonations = (response.data as List)
          .map((json) => RecurringDonationModel.fromJson(json))
          .toList();
      notifyListeners();
    } catch (_) {}
  }

  Future<bool> createRecurringDonation({
    required String templateName,
    required String foodName,
    required String foodCategory,
    required double typicalQuantity,
    required String quantityUnit,
    required String frequency,
    required String preferredPickupTime,
    required String pickupAddress,
    String? storageMethod,
    String? packagingCondition,
  }) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/recurring/create', data: {
        'template_name': templateName,
        'food_name': foodName,
        'food_category': foodCategory,
        'typical_quantity': typicalQuantity,
        'quantity_unit': quantityUnit,
        'frequency': frequency,
        'preferred_pickup_time': preferredPickupTime,
        'pickup_address': pickupAddress,
        'storage_method': storageMethod,
        'packaging_condition': packagingCondition,
      });
      await fetchRecurringDonations();
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> instantiateTodayDonation(int recurringId) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/recurring/$recurringId/instantiate');
      await fetchDonations(myDonationsOnly: true);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteRecurringDonation(int recurringId) async {
    try {
      await _apiClient.dio.delete('/donations/recurring/$recurringId');
      await fetchRecurringDonations();
      return true;
    } catch (_) {
      return false;
    }
  }

  // ── Certificate & CSR Impact Summary ──────────────────────────────────────
  Future<CertificateModel?> fetchCertificate(int donationId) async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/certificate');
      _certificate = CertificateModel.fromJson(response.data);
      _isLoading = false;
      notifyListeners();
      return _certificate;
    } catch (_) {
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  Future<CSRImpactSummaryModel?> fetchCSRSummary() async {
    try {
      final response = await _apiClient.dio.get('/donations/csr/summary');
      _csrSummary = CSRImpactSummaryModel.fromJson(response.data);
      notifyListeners();
      return _csrSummary;
    } catch (_) {
      return null;
    }
  }

  Future<DonorImpactSummaryModel?> fetchDonorImpactSummary() async {
    try {
      final response = await _apiClient.dio.get('/donations/donor/impact-summary');
      _donorImpact = DonorImpactSummaryModel.fromJson(response.data);
      notifyListeners();
      return _donorImpact;
    } catch (_) {
      return null;
    }
  }

  // ── Two-Way Ratings ───────────────────────────────────────────────────────
  Future<bool> submitRating({
    required int donationId,
    required int toUserId,
    required String roleTo,
    required int ratingScore,
    String? feedback,
    String? tags,
  }) async {
    try {
      await _apiClient.dio.post('/donations/$donationId/rate', data: {
        'donation_id': donationId,
        'to_user_id': toUserId,
        'role_to': roleTo,
        'rating_score': ratingScore,
        'feedback': feedback,
        'tags': tags,
      });
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> fetchRatings(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/ratings');
      _ratings = (response.data as List)
          .map((json) => RatingModel.fromJson(json))
          .toList();
      notifyListeners();
    } catch (_) {}
  }

  /// Securely retrieves verification code & expiration metadata for donor
  Future<Map<String, dynamic>?> fetchVerificationCode(int donationId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/verification-code');
      _isLoading = false;
      notifyListeners();
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      if (e.response?.data != null && e.response?.data is Map && e.response?.data['detail'] != null) {
        _errorMessage = e.response?.data['detail'].toString();
      } else {
        _errorMessage = e.error?.toString() ?? 'Unable to load verification code.';
      }
      _isLoading = false;
      notifyListeners();
      return null;
    } catch (e) {
      _errorMessage = 'Unable to load verification code.';
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  /// Requests server-side regeneration of 6-digit OTP
  Future<Map<String, dynamic>?> regenerateOtp(int donationId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.post('/donations/$donationId/regenerate-otp');
      _isLoading = false;
      notifyListeners();
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      if (e.response?.data != null && e.response?.data is Map && e.response?.data['detail'] != null) {
        _errorMessage = e.response?.data['detail'].toString();
      } else {
        _errorMessage = e.error?.toString() ?? 'Failed to regenerate verification code.';
      }
      _isLoading = false;
      notifyListeners();
      return null;
    } catch (e) {
      _errorMessage = 'Failed to regenerate verification code.';
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  // ─── RESCUE FEEDBACK & ISSUES ─────────────────────────────────────────────

  Future<bool> submitRescueFeedback(int donationId, RescueFeedbackModel feedback) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post(
        '/donations/$donationId/feedback',
        data: feedback.toJson(),
      );
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = 'Failed to submit feedback.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> reportRescueIssue({
    required int donationId,
    required String category,
    required String description,
    bool isFoodSafetyIncident = false,
    String? foodSafetyDetails,
    String? evidenceUrl,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post(
        '/donations/$donationId/issues',
        data: {
          'category': category,
          'description': description,
          'is_food_safety_incident': isFoodSafetyIncident,
          if (foodSafetyDetails != null) 'food_safety_details': foodSafetyDetails,
          if (evidenceUrl != null) 'evidence_url': evidenceUrl,
        },
      );
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = 'Failed to report issue.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<List<RescueFeedbackModel>> fetchRescueFeedback(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/feedback');
      return (response.data as List)
          .map((json) => RescueFeedbackModel.fromJson(json))
          .toList();
    } catch (e) {
      return [];
    }
  }

  Future<List<RescueIssueReportModel>> fetchRescueIssues(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/issues');
      return (response.data as List)
          .map((json) => RescueIssueReportModel.fromJson(json))
          .toList();
    } catch (e) {
      return [];
    }
  }

  Future<ReliabilityProfileModel?> fetchUserReliability(int userId) async {
    try {
      final response = await _apiClient.dio.get('/users/$userId/reliability');
      return ReliabilityProfileModel.fromJson(response.data);
    } catch (e) {
      return null;
    }
  }

  Future<PerformanceProfile?> fetchMyPerformance() async {
    try {
      final response = await _apiClient.dio.get('/users/me/performance');
      return PerformanceProfile.fromJson(response.data);
    } catch (e) {
      return null;
    }
  }

  Future<PerformanceProfile?> fetchUserPerformance(int userId) async {
    try {
      final response = await _apiClient.dio.get('/users/$userId/performance');
      return PerformanceProfile.fromJson(response.data);
    } catch (e) {
      return null;
    }
  }

  // ─── Final Core Enhancements: Tracking, Rematching & Safety Check ─────────

  /// Validates food safety self-check declaration before posting
  Future<FoodSafetyCheckModel?> validateFoodSafetyCheck(FoodSafetyCheckModel check) async {
    try {
      final response = await _apiClient.dio.post(
        '/donations/validate-safety-check',
        data: check.toJson(),
      );
      return FoodSafetyCheckModel.fromJson(response.data);
    } catch (e) {
      return null;
    }
  }

  /// Fetches real-time operational rescue tracking telemetry
  Future<RescueTrackingModel?> fetchRescueTracking(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/tracking');
      return RescueTrackingModel.fromJson(response.data);
    } catch (e) {
      return null;
    }
  }

  /// Triggers automated dynamic rematching for an active rescue
  Future<Map<String, dynamic>?> triggerRematch(int donationId, {String? reason}) async {
    try {
      _isLoading = true;
      notifyListeners();
      final response = await _apiClient.dio.post(
        '/donations/$donationId/rematch',
        data: {'reason': reason ?? 'Urgent reassignment requested'},
      );
      await fetchDonationDetail(donationId);
      _isLoading = false;
      notifyListeners();
      return response.data as Map<String, dynamic>;
    } catch (e) {
      _errorMessage = 'Failed to execute rematch.';
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  /// Transmits volunteer location telemetry
  Future<Map<String, dynamic>?> updateVolunteerLocation({
    required double latitude,
    required double longitude,
    int? donationId,
    int? assignmentId,
    double? speedKmh,
    double? heading,
    double? batteryLevel,
  }) async {
    try {
      final response = await _apiClient.dio.post('/volunteers/location', data: {
        'latitude': latitude,
        'longitude': longitude,
        if (donationId != null) 'donation_id': donationId,
        if (assignmentId != null) 'assignment_id': assignmentId,
        if (speedKmh != null) 'speed_kmh': speedKmh,
        if (heading != null) 'heading': heading,
        if (batteryLevel != null) 'battery_level': batteryLevel,
      });
      return response.data as Map<String, dynamic>;
    } catch (e) {
      return null;
    }
  }
}



