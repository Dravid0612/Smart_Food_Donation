class RescueFeedbackModel {
  final int id;
  final int donationId;
  final int authorId;
  final String authorRole;
  final String? authorName;
  final int? targetUserId;
  final int? targetNgoId;
  final int overallRating;

  // Donor Dimensions
  final String? pickupTimeliness;
  final String? handoverExperience;
  final String? communicationQuality;
  final String? appExperience;

  // NGO Dimensions
  final String? foodConditionRating;
  final String? quantityAccuracy;
  final String? packagingQuality;
  final String? volunteerPunctuality;
  final String? volunteerProfessionalism;

  // Volunteer Dimensions
  final String? donorReadiness;
  final String? pickupLocationClarity;
  final String? packagingReadiness;
  final String? ngoReceivingReadiness;

  final String? comment;
  final DateTime createdAt;

  RescueFeedbackModel({
    required this.id,
    required this.donationId,
    required this.authorId,
    required this.authorRole,
    this.authorName,
    this.targetUserId,
    this.targetNgoId,
    required this.overallRating,
    this.pickupTimeliness,
    this.handoverExperience,
    this.communicationQuality,
    this.appExperience,
    this.foodConditionRating,
    this.quantityAccuracy,
    this.packagingQuality,
    this.volunteerPunctuality,
    this.volunteerProfessionalism,
    this.donorReadiness,
    this.pickupLocationClarity,
    this.packagingReadiness,
    this.ngoReceivingReadiness,
    this.comment,
    required this.createdAt,
  });

  factory RescueFeedbackModel.fromJson(Map<String, dynamic> json) {
    return RescueFeedbackModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      donationId: json['donation_id'] is int ? json['donation_id'] : int.tryParse(json['donation_id'].toString()) ?? 0,
      authorId: json['author_id'] is int ? json['author_id'] : int.tryParse(json['author_id'].toString()) ?? 0,
      authorRole: json['author_role'] ?? 'donor',
      authorName: json['author_name'],
      targetUserId: json['target_user_id'] is int ? json['target_user_id'] : null,
      targetNgoId: json['target_ngo_id'] is int ? json['target_ngo_id'] : null,
      overallRating: json['overall_rating'] is int ? json['overall_rating'] : int.tryParse(json['overall_rating'].toString()) ?? 5,
      pickupTimeliness: json['pickup_timeliness'],
      handoverExperience: json['handover_experience'],
      communicationQuality: json['communication_quality'],
      appExperience: json['app_experience'],
      foodConditionRating: json['food_condition_rating'],
      quantityAccuracy: json['quantity_accuracy'],
      packagingQuality: json['packaging_quality'],
      volunteerPunctuality: json['volunteer_punctuality'],
      volunteerProfessionalism: json['volunteer_professionalism'],
      donorReadiness: json['donor_readiness'],
      pickupLocationClarity: json['pickup_location_clarity'],
      packagingReadiness: json['packaging_readiness'],
      ngoReceivingReadiness: json['ngo_receiving_readiness'],
      comment: json['comment'],
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) ?? DateTime.now() : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'overall_rating': overallRating,
      if (pickupTimeliness != null) 'pickup_timeliness': pickupTimeliness,
      if (handoverExperience != null) 'handover_experience': handoverExperience,
      if (communicationQuality != null) 'communication_quality': communicationQuality,
      if (appExperience != null) 'app_experience': appExperience,
      if (foodConditionRating != null) 'food_condition_rating': foodConditionRating,
      if (quantityAccuracy != null) 'quantity_accuracy': quantityAccuracy,
      if (packagingQuality != null) 'packaging_quality': packagingQuality,
      if (volunteerPunctuality != null) 'volunteer_punctuality': volunteerPunctuality,
      if (volunteerProfessionalism != null) 'volunteer_professionalism': volunteerProfessionalism,
      if (donorReadiness != null) 'donor_readiness': donorReadiness,
      if (pickupLocationClarity != null) 'pickup_location_clarity': pickupLocationClarity,
      if (packagingReadiness != null) 'packaging_readiness': packagingReadiness,
      if (ngoReceivingReadiness != null) 'ngo_receiving_readiness': ngoReceivingReadiness,
      if (comment != null && comment!.isNotEmpty) 'comment': comment,
    };
  }
}

class RescueIssueReportModel {
  final int id;
  final int donationId;
  final String? foodName;
  final int reporterId;
  final String? reporterName;
  final String reporterRole;
  final int? reportedUserId;
  final String? reportedUserName;
  final int? reportedNgoId;
  final String? reportedNgoName;
  final String category;
  final String severity;
  final bool isFoodSafetyIncident;
  final String? foodSafetyDetails;
  final String description;
  final String? evidenceUrl;
  final String status;
  final String? adminNotes;
  final int? resolvedBy;
  final String? resolverName;
  final DateTime createdAt;
  final int reporterHistoryCount;

  RescueIssueReportModel({
    required this.id,
    required this.donationId,
    this.foodName,
    required this.reporterId,
    this.reporterName,
    required this.reporterRole,
    this.reportedUserId,
    this.reportedUserName,
    this.reportedNgoId,
    this.reportedNgoName,
    required this.category,
    required this.severity,
    this.isFoodSafetyIncident = false,
    this.foodSafetyDetails,
    required this.description,
    this.evidenceUrl,
    required this.status,
    this.adminNotes,
    this.resolvedBy,
    this.resolverName,
    required this.createdAt,
    this.reporterHistoryCount = 0,
  });

  factory RescueIssueReportModel.fromJson(Map<String, dynamic> json) {
    return RescueIssueReportModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      donationId: json['donation_id'] is int ? json['donation_id'] : int.tryParse(json['donation_id'].toString()) ?? 0,
      foodName: json['food_name'],
      reporterId: json['reporter_id'] is int ? json['reporter_id'] : int.tryParse(json['reporter_id'].toString()) ?? 0,
      reporterName: json['reporter_name'],
      reporterRole: json['reporter_role'] ?? 'donor',
      reportedUserId: json['reported_user_id'] is int ? json['reported_user_id'] : null,
      reportedUserName: json['reported_user_name'],
      reportedNgoId: json['reported_ngo_id'] is int ? json['reported_ngo_id'] : null,
      reportedNgoName: json['reported_ngo_name'],
      category: json['category'] ?? 'other',
      severity: json['severity'] ?? 'LOW',
      isFoodSafetyIncident: json['is_food_safety_incident'] is bool ? json['is_food_safety_incident'] : false,
      foodSafetyDetails: json['food_safety_details'],
      description: json['description'] ?? '',
      evidenceUrl: json['evidence_url'],
      status: json['status'] ?? 'OPEN',
      adminNotes: json['admin_notes'],
      resolvedBy: json['resolved_by'] is int ? json['resolved_by'] : null,
      resolverName: json['resolver_name'],
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) ?? DateTime.now() : DateTime.now(),
      reporterHistoryCount: json['reporter_history_count'] is int ? json['reporter_history_count'] : 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'category': category,
      'description': description,
      'is_food_safety_incident': isFoodSafetyIncident,
      if (foodSafetyDetails != null) 'food_safety_details': foodSafetyDetails,
      if (evidenceUrl != null) 'evidence_url': evidenceUrl,
    };
  }
}

class ReliabilityDimensionModel {
  final String name;
  final double score;
  final double weight;
  final String description;

  ReliabilityDimensionModel({
    required this.name,
    required this.score,
    required this.weight,
    required this.description,
  });

  factory ReliabilityDimensionModel.fromJson(Map<String, dynamic> json) {
    return ReliabilityDimensionModel(
      name: json['name'] ?? '',
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      weight: (json['weight'] as num?)?.toDouble() ?? 0.0,
      description: json['description'] ?? '',
    );
  }
}

class ReliabilityProfileModel {
  final int userId;
  final String name;
  final String role;
  final int totalCompletedRescues;
  final int totalAcceptedRescues;
  final int cancellationsCount;
  final int noShowsCount;
  final double onTimeRatePercent;
  final double completionRatePercent;
  final double averageServiceRating;
  final double overallReliabilityScore;
  final String trustTier;
  final List<String> trustBadges;
  final bool hasSufficientHistory;
  final int sampleSizeThreshold;
  final int recencyWindowRescues;
  final List<ReliabilityDimensionModel> dimensions;

  ReliabilityProfileModel({
    required this.userId,
    required this.name,
    required this.role,
    required this.totalCompletedRescues,
    required this.totalAcceptedRescues,
    required this.cancellationsCount,
    required this.noShowsCount,
    required this.onTimeRatePercent,
    required this.completionRatePercent,
    required this.averageServiceRating,
    required this.overallReliabilityScore,
    required this.trustTier,
    required this.trustBadges,
    required this.hasSufficientHistory,
    this.sampleSizeThreshold = 3,
    this.recencyWindowRescues = 10,
    required this.dimensions,
  });

  factory ReliabilityProfileModel.fromJson(Map<String, dynamic> json) {
    return ReliabilityProfileModel(
      userId: json['user_id'] is int ? json['user_id'] : int.tryParse(json['user_id'].toString()) ?? 0,
      name: json['name'] ?? '',
      role: json['role'] ?? 'user',
      totalCompletedRescues: json['total_completed_rescues'] is int ? json['total_completed_rescues'] : 0,
      totalAcceptedRescues: json['total_accepted_rescues'] is int ? json['total_accepted_rescues'] : 0,
      cancellationsCount: json['cancellations_count'] is int ? json['cancellations_count'] : 0,
      noShowsCount: json['no_shows_count'] is int ? json['no_shows_count'] : 0,
      onTimeRatePercent: (json['on_time_rate_percent'] as num?)?.toDouble() ?? 100.0,
      completionRatePercent: (json['completion_rate_percent'] as num?)?.toDouble() ?? 100.0,
      averageServiceRating: (json['average_service_rating'] as num?)?.toDouble() ?? 5.0,
      overallReliabilityScore: (json['overall_reliability_score'] as num?)?.toDouble() ?? 95.0,
      trustTier: json['trust_tier'] ?? 'Active Partner',
      trustBadges: (json['trust_badges'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      hasSufficientHistory: json['has_sufficient_history'] is bool ? json['has_sufficient_history'] : false,
      sampleSizeThreshold: json['sample_size_threshold'] is int ? json['sample_size_threshold'] : 3,
      recencyWindowRescues: json['recency_window_rescues'] is int ? json['recency_window_rescues'] : 10,
      dimensions: (json['dimensions'] as List<dynamic>?)
              ?.map((e) => ReliabilityDimensionModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
