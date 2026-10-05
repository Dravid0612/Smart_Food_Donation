import 'package:flutter/material.dart';
import '../core/api/api_client.dart';
import '../models/user_model.dart';
import '../models/ngo_model.dart';
import '../models/donation_model.dart';
import '../models/feedback_model.dart';
import '../models/performance_model.dart';
import '../models/admin_operations_model.dart';

class AdminProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();

  Map<String, dynamic>? _statistics;
  List<UserModel> _allUsers = [];
  List<NgoModel> _allNgos = [];
  List<DonationModel> _allDonations = [];
  Map<String, dynamic>? _feedbackOverview;
  List<RescueIssueReportModel> _adminIssues = [];
  List<RescueFeedbackModel> _adminFeedbacks = [];

  // Food Rescue Control Center State
  AdminReceivingSummaryModel? _receivingSummary;
  List<AdminReceivingItemModel> _receivingItems = [];
  AdminRescueDetailModel? _selectedRescueDetail;
  List<AdminNgoCapacityModel> _ngoCapacities = [];
  List<AdminCategoryBreakdownItemModel> _categoryBreakdown = [];
  AdminMonthlyReportModel? _monthlyReport;
  AdminRepeatDonorInsightsModel? _wasteInsights;
  String _selectedTab = 'ALL';
  String? _searchQuery;
  String? _selectedCategory;
  bool _isReceivingLoading = false;

  bool _isLoading = false;
  String? _errorMessage;

  Map<String, dynamic>? get statistics => _statistics;
  List<UserModel> get allUsers => _allUsers;
  List<NgoModel> get allNgos => _allNgos;
  List<NgoModel> get unverifiedNgos => _allNgos.where((n) => !n.isVerified).toList();
  List<DonationModel> get allDonations => _allDonations;
  Map<String, dynamic>? get feedbackOverview => _feedbackOverview;
  List<RescueIssueReportModel> get adminIssues => _adminIssues;
  List<RescueFeedbackModel> get adminFeedbacks => _adminFeedbacks;

  AdminReceivingSummaryModel? get receivingSummary => _receivingSummary;
  List<AdminReceivingItemModel> get receivingItems => _receivingItems;
  AdminRescueDetailModel? get selectedRescueDetail => _selectedRescueDetail;
  List<AdminNgoCapacityModel> get ngoCapacities => _ngoCapacities;
  List<AdminCategoryBreakdownItemModel> get categoryBreakdown => _categoryBreakdown;
  AdminMonthlyReportModel? get monthlyReport => _monthlyReport;
  AdminRepeatDonorInsightsModel? get wasteInsights => _wasteInsights;
  String get selectedTab => _selectedTab;
  String? get searchQuery => _searchQuery;
  String? get selectedCategory => _selectedCategory;
  bool get isReceivingLoading => _isReceivingLoading;

  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> fetchAdminStatistics() async {
    _isLoading = true;
    _errorMessage = null;
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
    if (_isMockForTesting) return;
    _isLoading = true;
    _errorMessage = null;
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
    if (_isMockForTesting) return;
    _isLoading = true;
    _errorMessage = null;
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
    if (_isMockForTesting) return;
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final response = await _apiClient.dio.get('/donations');
      _allDonations = (response.data as List).map((j) => DonationModel.fromJson(j)).toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> verifyNgo(int ngoId) async {
    if (_isMockForTesting) {
      final idx = _allNgos.indexWhere((n) => n.id == ngoId);
      if (idx != -1) {
        _allNgos[idx] = _allNgos[idx].copyWith(isVerified: true);
        notifyListeners();
      }
      return true;
    }
    try {
      await _apiClient.dio.post('/admin/ngos/$ngoId/verify');
      await fetchAllNgos();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> rejectNgo(int ngoId, {required String reason}) async {
    if (_isMockForTesting) {
      final idx = _allNgos.indexWhere((n) => n.id == ngoId);
      if (idx != -1) {
        _allNgos.removeAt(idx);
        notifyListeners();
      }
      return true;
    }
    try {
      await _apiClient.dio.post(
        '/admin/ngos/$ngoId/reject',
        queryParameters: {'reason': reason},
      );
      await fetchAllNgos();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> toggleUserActive(int userId) async {
    if (_isMockForTesting) {
      final idx = _allUsers.indexWhere((u) => u.id == userId);
      if (idx != -1) {
        _allUsers[idx] = _allUsers[idx].copyWith(isActive: !_allUsers[idx].isActive);
        notifyListeners();
      }
      return true;
    }
    try {
      await _apiClient.dio.put('/admin/users/$userId/toggle-active');
      await fetchAllUsers();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> triggerBatchMatchmaking() async {
    try {
      await _apiClient.dio.get('/donations/batch-match/run');
      await fetchAdminStatistics();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> escalateDonation(int donationId) async {
    try {
      await _apiClient.dio.post('/donations/$donationId/escalate');
      await fetchAllDonations();
      return true;
    } catch (e) {
      return false;
    }
  }

  // ─── ADMIN FEEDBACK & ISSUE INTERVENTION QUEUE ────────────────────────────

  Future<void> fetchFeedbackOverview() async {
    try {
      final response = await _apiClient.dio.get('/admin/feedback/overview');
      _feedbackOverview = response.data as Map<String, dynamic>;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> fetchAdminIssues({
    String? status,
    String? severity,
    String? category,
  }) async {
    _isLoading = true;
    notifyListeners();
    try {
      final Map<String, dynamic> params = {};
      if (status != null && status.isNotEmpty && status != 'ALL') params['status'] = status;
      if (severity != null && severity.isNotEmpty && severity != 'ALL') params['severity'] = severity;
      if (category != null && category.isNotEmpty && category != 'ALL') params['category'] = category;

      final response = await _apiClient.dio.get('/admin/issues', queryParameters: params);
      _adminIssues = (response.data as List)
          .map((j) => RescueIssueReportModel.fromJson(j))
          .toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchAdminFeedbacks({String? role, int? minRating}) async {
    try {
      final Map<String, dynamic> params = {};
      if (role != null && role.isNotEmpty) params['role'] = role;
      if (minRating != null) params['min_rating'] = minRating;

      final response = await _apiClient.dio.get('/admin/feedback', queryParameters: params);
      _adminFeedbacks = (response.data as List)
          .map((j) => RescueFeedbackModel.fromJson(j))
          .toList();
      notifyListeners();
    } catch (_) {}
  }

  Future<bool> resolveAdminIssue(
    int issueId, {
    required String status,
    String? adminNotes,
    double? reliabilityPenalty,
  }) async {
    try {
      await _apiClient.dio.post(
        '/admin/issues/$issueId/resolve',
        data: {
          'status': status,
          if (adminNotes != null) 'admin_notes': adminNotes,
          if (reliabilityPenalty != null) 'reliability_penalty': reliabilityPenalty,
        },
      );
      await fetchAdminIssues();
      await fetchFeedbackOverview();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> dismissAdminIssue(int issueId) async {
    try {
      await _apiClient.dio.post('/admin/issues/$issueId/dismiss');
      await fetchAdminIssues();
      await fetchFeedbackOverview();
      return true;
    } catch (e) {
      return false;
    }
  }

  // ─── Performance & Matching Intelligence ─────────────────────────────────

  Future<AdminPerformanceOverview> fetchPerformanceOverview() async {
    final response = await _apiClient.dio.get('/admin/performance/overview');
    return AdminPerformanceOverview.fromJson(response.data);
  }

  Future<RescueFailureAnalytics> fetchFailureAnalytics() async {
    final response = await _apiClient.dio.get('/admin/performance/failures');
    return RescueFailureAnalytics.fromJson(response.data);
  }

  Future<List<NeedsReviewParticipant>> fetchNeedsReviewQueue() async {
    final response = await _apiClient.dio.get('/admin/performance/needs-review');
    return (response.data as List)
        .map((j) => NeedsReviewParticipant.fromJson(j))
        .toList();
  }

  Future<List<SuspiciousFeedbackAlert>> fetchSuspiciousFeedbackAlerts() async {
    final response = await _apiClient.dio.get('/admin/performance/suspicious-feedback');
    return (response.data as List)
        .map((j) => SuspiciousFeedbackAlert.fromJson(j))
        .toList();
  }

  Future<bool> executePerformanceAction({
    required int userId,
    required String action,
    String? notes,
    double? deprioritizeFactor,
  }) async {
    try {
      await _apiClient.dio.post(
        '/admin/users/$userId/performance-action',
        data: {
          'action': action,
          if (notes != null) 'notes': notes,
          if (deprioritizeFactor != null) 'deprioritize_factor': deprioritizeFactor,
        },
      );
      return true;
    } catch (e) {
      return false;
    }
  }

  // ─── Food Rescue Operations Control Center ───────────────────────────────

  bool _isMockForTesting = false;

  Future<void> fetchReceivingSummary() async {
    if (_isMockForTesting) return;
    try {
      final response = await _apiClient.dio.get('/admin/receiving/summary');
      _receivingSummary = AdminReceivingSummaryModel.fromJson(response.data);
      notifyListeners();
    } catch (_) {}
  }

  Future<void> fetchReceivingList({
    String? tab,
    String? search,
    String? category,
    String? urgency,
  }) async {
    if (_isMockForTesting) return;
    _isReceivingLoading = true;
    if (tab != null) _selectedTab = tab;
    if (search != null) _searchQuery = search;
    if (category != null) _selectedCategory = category;
    notifyListeners();

    try {
      final Map<String, dynamic> params = {
        'tab': _selectedTab,
        'page': 1,
        'page_size': 50,
      };
      if (_searchQuery != null && _searchQuery!.trim().isNotEmpty) {
        params['search'] = _searchQuery!.trim();
      }
      if (_selectedCategory != null && _selectedCategory!.isNotEmpty && _selectedCategory != 'ALL') {
        params['category'] = _selectedCategory;
      }
      if (urgency != null && urgency.isNotEmpty && urgency != 'ALL') {
        params['urgency'] = urgency;
      }

      final response = await _apiClient.dio.get('/admin/receiving', queryParameters: params);
      final listData = response.data['items'] as List;
      _receivingItems = listData.map((j) => AdminReceivingItemModel.fromJson(j)).toList();
      _isReceivingLoading = false;
      notifyListeners();
    } catch (e) {
      _isReceivingLoading = false;
      notifyListeners();
    }
  }

  Future<AdminRescueDetailModel?> fetchRescueDetail(int donationId) async {
    if (_isMockForTesting && _selectedRescueDetail != null) {
      return _selectedRescueDetail;
    }
    try {
      final response = await _apiClient.dio.get('/admin/rescues/$donationId');
      _selectedRescueDetail = AdminRescueDetailModel.fromJson(response.data);
      notifyListeners();
      return _selectedRescueDetail;
    } catch (e) {
      return null;
    }
  }

  Future<bool> submitIntervention(
    int donationId,
    String reasonCode, {
    String? notes,
    String? actionType,
    String? targetStatus,
    int? replacementVolunteerId,
  }) async {
    if (_isMockForTesting) return true;
    try {
      await _apiClient.dio.post(
        '/admin/interventions',
        data: {
          'donation_id': donationId,
          'reason_code': reasonCode,
          if (notes != null) 'notes': notes,
          if (actionType != null) 'action_type': actionType,
          if (targetStatus != null) 'target_status': targetStatus,
          if (replacementVolunteerId != null) 'replacement_volunteer_id': replacementVolunteerId,
        },
      );
      await fetchReceivingSummary();
      await fetchReceivingList();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<void> fetchNgoCapacities() async {
    if (_isMockForTesting) return;
    try {
      final response = await _apiClient.dio.get('/admin/ngos/capacity');
      _ngoCapacities = (response.data as List)
          .map((j) => AdminNgoCapacityModel.fromJson(j))
          .toList();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> fetchCategoryBreakdown() async {
    if (_isMockForTesting) return;
    try {
      final response = await _apiClient.dio.get('/admin/category-breakdown');
      final list = response.data['categories'] as List;
      _categoryBreakdown = list
          .map((j) => AdminCategoryBreakdownItemModel.fromJson(j))
          .toList();
      notifyListeners();
    } catch (_) {}
  }

  void setReceivingDataForTesting({
    AdminReceivingSummaryModel? summary,
    List<AdminReceivingItemModel>? items,
    List<AdminNgoCapacityModel>? capacities,
    List<AdminCategoryBreakdownItemModel>? categories,
  }) {
    _isMockForTesting = true;
    if (summary != null) _receivingSummary = summary;
    if (items != null) _receivingItems = items;
    if (capacities != null) _ngoCapacities = capacities;
    if (categories != null) _categoryBreakdown = categories;
    notifyListeners();
  }

  void setUsersForTesting(List<UserModel> users) {
    _isMockForTesting = true;
    _allUsers = users;
    notifyListeners();
  }

  void setNgosForTesting(List<NgoModel> ngos) {
    _isMockForTesting = true;
    _allNgos = ngos;
    notifyListeners();
  }

  void setRescueDetailForTesting(AdminRescueDetailModel? detail) {
    _isMockForTesting = true;
    _selectedRescueDetail = detail;
    notifyListeners();
  }

  void setDonationsForTesting(List<DonationModel> donations) {
    _isMockForTesting = true;
    _allDonations = donations;
    notifyListeners();
  }

  void setMonthlyReportForTesting(AdminMonthlyReportModel? report) {
    _isMockForTesting = true;
    _monthlyReport = report;
    notifyListeners();
  }

  void setWasteInsightsForTesting(AdminRepeatDonorInsightsModel? insights) {
    _isMockForTesting = true;
    _wasteInsights = insights;
    notifyListeners();
  }

  Future<AdminMonthlyReportModel?> fetchMonthlyImpactReport({String? month}) async {
    if (_isMockForTesting && _monthlyReport != null) return _monthlyReport;
    try {
      final Map<String, dynamic> params = {};
      if (month != null) params['month'] = month;
      final response = await _apiClient.dio.get('/admin/reports/monthly', queryParameters: params);
      _monthlyReport = AdminMonthlyReportModel.fromJson(response.data);
      notifyListeners();
      return _monthlyReport;
    } catch (_) {
      return null;
    }
  }

  Future<AdminRepeatDonorInsightsModel?> fetchRepeatDonorWasteInsights() async {
    if (_isMockForTesting && _wasteInsights != null) return _wasteInsights;
    try {
      final response = await _apiClient.dio.get('/admin/insights/repeat-donors');
      _wasteInsights = AdminRepeatDonorInsightsModel.fromJson(response.data);
      notifyListeners();
      return _wasteInsights;
    } catch (_) {
      return null;
    }
  }
}



