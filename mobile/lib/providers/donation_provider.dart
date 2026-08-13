import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../models/donation_model.dart';
import '../models/recommendation_model.dart';

class DonationProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();

  List<DonationModel> _donations = [];
  DonationModel? _currentDetail;
  List<NgoRecommendationModel> _ngoRecommendations = [];
  List<VolunteerRecommendationModel> _volunteerRecommendations = [];
  bool _isLoading = false;
  String? _errorMessage;

  List<DonationModel> get donations => _donations;
  DonationModel? get currentDetail => _currentDetail;
  List<NgoRecommendationModel> get ngoRecommendations => _ngoRecommendations;
  List<VolunteerRecommendationModel> get volunteerRecommendations => _volunteerRecommendations;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

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
    required String foodCategory,
    required double quantity,
    required String quantityUnit,
    required DateTime preparationTime,
    required DateTime expiryTime,
    required String pickupAddress,
    String? description,
    double? latitude,
    double? longitude,
    String? imageUrl,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations', data: {
        'food_name': foodName,
        'food_category': foodCategory,
        'quantity': quantity,
        'quantity_unit': quantityUnit,
        'preparation_time': preparationTime.toUtc().toIso8601String(),
        'expiry_time': expiryTime.toUtc().toIso8601String(),
        'pickup_address': pickupAddress,
        'description': description,
        'latitude': latitude,
        'longitude': longitude,
        'image_url': imageUrl,
      });

      await fetchDonations();
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

  Future<bool> acceptDonation(int donationId) async {
    _isLoading = true;
    notifyListeners();
    try {
      await _apiClient.dio.post('/donations/$donationId/accept');
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
}
