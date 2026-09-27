class DonationHistoryModel {
  final int id;
  final int donationId;
  final String? oldStatus;
  final String newStatus;
  final int? changedBy;
  final String? remarks;
  final String createdAt;

  DonationHistoryModel({
    required this.id,
    required this.donationId,
    this.oldStatus,
    required this.newStatus,
    this.changedBy,
    this.remarks,
    required this.createdAt,
  });

  factory DonationHistoryModel.fromJson(Map<String, dynamic> json) {
    return DonationHistoryModel(
      id: json['id'],
      donationId: json['donation_id'],
      oldStatus: json['old_status'],
      newStatus: json['new_status'] ?? '',
      changedBy: json['changed_by'],
      remarks: json['remarks'],
      createdAt: json['created_at'] ?? '',
    );
  }
}

class FoodRescueWindowModel {
  final String assessmentStatus;
  final String foodType;
  final String foodCategory;
  final String ruleSource;
  final String ruleVersion;
  final String ruleCoverage;
  final bool isCustom;
  final String visualCondition;
  final String estimatedWindowStart;
  final String estimatedWindowEnd;
  final int remainingMinutes;
  final String estimatedWindowDisplay;
  final String urgencyLevel;
  final double urgencyScore;
  final double confidence;
  final List<String> reasons;
  final String safetyDisclaimer;

  FoodRescueWindowModel({
    this.assessmentStatus = 'ADVISORY',
    required this.foodType,
    required this.foodCategory,
    this.ruleSource = 'Verified Project Knowledge Rules',
    this.ruleVersion = '2026.1',
    this.ruleCoverage = 'HIGH',
    this.isCustom = false,
    required this.visualCondition,
    required this.estimatedWindowStart,
    required this.estimatedWindowEnd,
    required this.remainingMinutes,
    required this.estimatedWindowDisplay,
    required this.urgencyLevel,
    required this.urgencyScore,
    required this.confidence,
    this.reasons = const [],
    this.safetyDisclaimer = 'Visual assessment only. This is an advisory estimate and does not certify food safety.',
  });

  factory FoodRescueWindowModel.fromJson(Map<String, dynamic> json) {
    return FoodRescueWindowModel(
      assessmentStatus: json['assessment_status'] ?? 'ADVISORY',
      foodType: json['food_type'] ?? '',
      foodCategory: json['food_category'] ?? '',
      ruleSource: json['rule_source'] ?? 'Verified Project Knowledge Rules',
      ruleVersion: json['rule_version'] ?? '2026.1',
      ruleCoverage: json['rule_coverage'] ?? 'HIGH',
      isCustom: json['is_custom'] ?? false,
      visualCondition: json['visual_condition'] ?? 'GOOD',
      estimatedWindowStart: json['estimated_window_start'] ?? '',
      estimatedWindowEnd: json['estimated_window_end'] ?? '',
      remainingMinutes: json['remaining_minutes'] ?? 0,
      estimatedWindowDisplay: json['estimated_window_display'] ?? '',
      urgencyLevel: json['urgency_level'] ?? 'FRESH',
      urgencyScore: (json['urgency_score'] as num?)?.toDouble() ?? 0.0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.88,
      reasons: (json['reasons'] as List?)?.map((e) => e.toString()).toList() ?? [],
      safetyDisclaimer: json['safety_disclaimer'] ?? 'Visual assessment only. This is an advisory estimate and does not certify food safety.',
    );
  }
}

class RescueFeasibilityModel {
  final String feasibilityStatus;
  final String feasibilityLabel;
  final bool isFeasible;
  final double estimatedPickupMinutes;
  final double estimatedTravelMinutes;
  final double ngoIntakeMinutes;
  final double safetyBufferMinutes;
  final double totalRequiredMinutes;
  final int remainingBufferMinutes;
  final String explanation;

  RescueFeasibilityModel({
    required this.feasibilityStatus,
    required this.feasibilityLabel,
    required this.isFeasible,
    this.estimatedPickupMinutes = 15.0,
    this.estimatedTravelMinutes = 20.0,
    this.ngoIntakeMinutes = 10.0,
    this.safetyBufferMinutes = 15.0,
    this.totalRequiredMinutes = 60.0,
    this.remainingBufferMinutes = 0,
    required this.explanation,
  });

  factory RescueFeasibilityModel.fromJson(Map<String, dynamic> json) {
    return RescueFeasibilityModel(
      feasibilityStatus: json['feasibility_status'] ?? 'RESCUE_FEASIBLE',
      feasibilityLabel: json['feasibility_label'] ?? 'Rescue Feasible',
      isFeasible: json['is_feasible'] ?? true,
      estimatedPickupMinutes: (json['estimated_pickup_minutes'] as num?)?.toDouble() ?? 15.0,
      estimatedTravelMinutes: (json['estimated_travel_minutes'] as num?)?.toDouble() ?? 20.0,
      ngoIntakeMinutes: (json['ngo_intake_minutes'] as num?)?.toDouble() ?? 10.0,
      safetyBufferMinutes: (json['safety_buffer_minutes'] as num?)?.toDouble() ?? 15.0,
      totalRequiredMinutes: (json['total_required_minutes'] as num?)?.toDouble() ?? 60.0,
      remainingBufferMinutes: json['remaining_buffer_minutes'] ?? 0,
      explanation: json['explanation'] ?? '',
    );
  }
}

class FoodSafetyCheckModel {
  final bool humanConsumption;
  final bool hygienicHandling;
  final bool appropriateStorage;
  final bool contaminationFree;
  final bool suitableCondition;
  final bool isEligible;
  final String status;
  final List<String> failedDeclarations;
  final String? warningMessage;
  final String? guidance;
  final String disclaimer;

  FoodSafetyCheckModel({
    this.humanConsumption = true,
    this.hygienicHandling = true,
    this.appropriateStorage = true,
    this.contaminationFree = true,
    this.suitableCondition = true,
    this.isEligible = true,
    this.status = 'PASSED',
    this.failedDeclarations = const [],
    this.warningMessage,
    this.guidance,
    this.disclaimer = 'Advisory screening declaration only. Does not replace laboratory certification.',
  });

  factory FoodSafetyCheckModel.fromJson(Map<String, dynamic> json) {
    return FoodSafetyCheckModel(
      humanConsumption: json['human_consumption'] ?? true,
      hygienicHandling: json['hygienic_handling'] ?? true,
      appropriateStorage: json['appropriate_storage'] ?? true,
      contaminationFree: json['contamination_free'] ?? true,
      suitableCondition: json['suitable_condition'] ?? true,
      isEligible: json['is_eligible'] ?? true,
      status: json['status'] ?? 'PASSED',
      failedDeclarations: (json['failed_declarations'] as List?)?.map((e) => e.toString()).toList() ?? [],
      warningMessage: json['warning_message'],
      guidance: json['guidance'],
      disclaimer: json['disclaimer'] ?? 'Advisory screening declaration only. Does not replace laboratory certification.',
    );
  }

  Map<String, dynamic> toJson() => {
    'human_consumption': humanConsumption,
    'hygienic_handling': hygienicHandling,
    'appropriate_storage': appropriateStorage,
    'contamination_free': contaminationFree,
    'suitable_condition': suitableCondition,
  };
}

class TrackingStageItemModel {
  final String stage;
  final String label;
  final bool isCompleted;
  final bool isCurrent;
  final String? timestamp;
  final String? details;

  TrackingStageItemModel({
    required this.stage,
    required this.label,
    required this.isCompleted,
    required this.isCurrent,
    this.timestamp,
    this.details,
  });

  factory TrackingStageItemModel.fromJson(Map<String, dynamic> json) {
    return TrackingStageItemModel(
      stage: json['stage'] ?? '',
      label: json['label'] ?? '',
      isCompleted: json['is_completed'] ?? false,
      isCurrent: json['is_current'] ?? false,
      timestamp: json['timestamp'],
      details: json['details'],
    );
  }
}

class RescueTrackingModel {
  final int donationId;
  final String foodName;
  final double quantity;
  final String quantityUnit;
  final String status;
  final String trackingStatus;
  final String trackingStage;
  final String stageLabel;
  final String nextActionPrompt;
  final double? currentLatitude;
  final double? currentLongitude;
  final double? destinationLatitude;
  final double? destinationLongitude;
  final int? etaMinutes;
  final String etaDisplay;
  final double? distanceKm;
  final String? volunteerName;
  final String? volunteerPhone;
  final String volunteerVehicle;
  final String? donorName;
  final String? pickupAddress;
  final String? destinationAddress;
  final int remainingRescueWindowMinutes;
  final String feasibilityStatus;
  final bool isAtRisk;
  final bool isRematched;
  final int rematchCount;
  final String? rematchReason;
  final String? previousVolunteerName;
  final List<TrackingStageItemModel> stagesTimeline;
  final String? lastUpdatedAt;

  RescueTrackingModel({
    required this.donationId,
    required this.foodName,
    required this.quantity,
    required this.quantityUnit,
    required this.status,
    required this.trackingStatus,
    required this.trackingStage,
    required this.stageLabel,
    required this.nextActionPrompt,
    this.currentLatitude,
    this.currentLongitude,
    this.destinationLatitude,
    this.destinationLongitude,
    this.etaMinutes,
    required this.etaDisplay,
    this.distanceKm,
    this.volunteerName,
    this.volunteerPhone,
    this.volunteerVehicle = 'bike',
    this.donorName,
    this.pickupAddress,
    this.destinationAddress,
    this.remainingRescueWindowMinutes = 60,
    this.feasibilityStatus = 'RESCUE_FEASIBLE',
    this.isAtRisk = false,
    this.isRematched = false,
    this.rematchCount = 0,
    this.rematchReason,
    this.previousVolunteerName,
    this.stagesTimeline = const [],
    this.lastUpdatedAt,
  });

  factory RescueTrackingModel.fromJson(Map<String, dynamic> json) {
    var timeline = <TrackingStageItemModel>[];
    if (json['stages_timeline'] != null && json['stages_timeline'] is List) {
      timeline = (json['stages_timeline'] as List)
          .map((i) => TrackingStageItemModel.fromJson(i))
          .toList();
    }

    return RescueTrackingModel(
      donationId: json['donation_id'] ?? 0,
      foodName: json['food_name'] ?? '',
      quantity: (json['quantity'] as num?)?.toDouble() ?? 0.0,
      quantityUnit: json['quantity_unit'] ?? 'Meals',
      status: json['status'] ?? 'pending',
      trackingStatus: json['tracking_status'] ?? 'IDLE',
      trackingStage: json['tracking_stage'] ?? 'PENDING',
      stageLabel: json['stage_label'] ?? '',
      nextActionPrompt: json['next_action_prompt'] ?? '',
      currentLatitude: (json['current_latitude'] as num?)?.toDouble(),
      currentLongitude: (json['current_longitude'] as num?)?.toDouble(),
      destinationLatitude: (json['destination_latitude'] as num?)?.toDouble(),
      destinationLongitude: (json['destination_longitude'] as num?)?.toDouble(),
      etaMinutes: json['eta_minutes'],
      etaDisplay: json['eta_display'] ?? 'Estimating...',
      distanceKm: (json['distance_km'] as num?)?.toDouble(),
      volunteerName: json['volunteer_name'],
      volunteerPhone: json['volunteer_phone'],
      volunteerVehicle: json['volunteer_vehicle'] ?? 'bike',
      donorName: json['donor_name'],
      pickupAddress: json['pickup_address'],
      destinationAddress: json['destination_address'],
      remainingRescueWindowMinutes: json['remaining_rescue_window_minutes'] ?? 60,
      feasibilityStatus: json['feasibility_status'] ?? 'RESCUE_FEASIBLE',
      isAtRisk: json['is_at_risk'] ?? false,
      isRematched: json['is_rematched'] ?? false,
      rematchCount: json['rematch_count'] ?? 0,
      rematchReason: json['rematch_reason'],
      previousVolunteerName: json['previous_volunteer_name'],
      stagesTimeline: timeline,
      lastUpdatedAt: json['last_updated_at'],
    );
  }
}

class DonationModel {
  final int id;
  final int donorId;
  final String foodName;
  final String? foodType;
  final String foodSource; // 'KNOWN' vs 'CUSTOM'
  final String? customFoodName;
  final String? foodDescription;
  final String? majorIngredients;
  final String? description;
  final String foodCategory;
  final double quantity;
  final String quantityUnit;
  final String? quantityUnitLabel;
  final double? estimatedMeals;
  final String ruleCoverage;
  final String classificationSource;
  final double classificationConfidence;
  final String preparationTime;
  final String expiryTime;
  final String pickupAddress;
  final double? latitude;
  final double? longitude;
  final String? imageUrl;
  final String? storageMethod;
  final double? storageDurationHours;
  final bool storageContinuous;
  final String? storageHistoryJson;
  final String? packagingCondition;
  final String previouslyServed;
  final String exposureStatus;
  final String handlingStatus;
  final String? pickupDeadline;
  final String? estimatedWindowStart;
  final String? estimatedWindowEnd;
  final int? remainingMinutes;
  final String rescueUrgencyLevel;
  final String feasibilityStatus;
  final String? reasonsJson;
  final String? aiFoodDetected;
  final String? aiVisibleSpoilage;
  final String? aiDiscoloration;
  final String? aiPackagingIntact;
  final String? aiVisualCondition;
  final double? aiConfidenceScore;
  final int? conditionScore;
  final String? verificationOtp;
  final String? qrCodeToken;
  final bool isEmergency;
  final String? failureReason;
  final String status;
  final int? assignedNgoId;
  final int? assignedVolunteerId;
  final String createdAt;
  final String urgencyLevel;
  final String? donorName;
  final String? donorPhone;
  final String? ngoName;
  final String? volunteerName;
  final String? volunteerPhone;
  final FoodRescueWindowModel? rescueWindow;
  final RescueFeasibilityModel? feasibility;
  final List<DonationHistoryModel> history;

  // Real-Time Rescue Tracking
  final double? trackingLatitude;
  final double? trackingLongitude;
  final String? trackingLastUpdatedAt;
  final double? currentEtaMinutes;
  final double? currentDistanceKm;
  final String trackingStatus;

  // Dynamic Rematching & Reassignment
  final bool isRematched;
  final int rematchCount;
  final String? rematchReason;
  final int? previousVolunteerId;
  final String? previousVolunteerName;

  // Food-Safety Self-Check Screening
  final bool safetyCheckCompleted;
  final String safetyCheckStatus;
  final String? safetyCheckVersion;
  final Map<String, dynamic>? safetyCheckAnswers;
  final String pickupMode;

  DonationModel({
    required this.id,
    required this.donorId,
    required this.foodName,
    this.foodType,
    this.foodSource = 'KNOWN',
    this.customFoodName,
    this.foodDescription,
    this.majorIngredients,
    this.description,
    required this.foodCategory,
    required this.quantity,
    required this.quantityUnit,
    this.quantityUnitLabel,
    this.estimatedMeals,
    this.ruleCoverage = 'HIGH',
    this.classificationSource = 'rule_exact',
    this.classificationConfidence = 1.0,
    required this.preparationTime,
    required this.expiryTime,
    required this.pickupAddress,
    this.latitude,
    this.longitude,
    this.imageUrl,
    this.storageMethod,
    this.storageDurationHours,
    this.storageContinuous = true,
    this.storageHistoryJson,
    this.packagingCondition,
    this.previouslyServed = 'No',
    this.exposureStatus = 'No',
    this.handlingStatus = 'No',
    this.pickupDeadline,
    this.estimatedWindowStart,
    this.estimatedWindowEnd,
    this.remainingMinutes,
    this.rescueUrgencyLevel = 'FRESH',
    this.feasibilityStatus = 'RESCUE_FEASIBLE',
    this.reasonsJson,
    this.aiFoodDetected,
    this.aiVisibleSpoilage,
    this.aiDiscoloration,
    this.aiPackagingIntact,
    this.aiVisualCondition,
    this.aiConfidenceScore,
    this.conditionScore,
    this.verificationOtp,
    this.qrCodeToken,
    this.isEmergency = false,
    this.failureReason,
    required this.status,
    this.assignedNgoId,
    this.assignedVolunteerId,
    required this.createdAt,
    this.urgencyLevel = 'Fresh',
    this.donorName,
    this.donorPhone,
    this.ngoName,
    this.volunteerName,
    this.volunteerPhone,
    this.rescueWindow,
    this.feasibility,
    this.history = const [],
    this.trackingLatitude,
    this.trackingLongitude,
    this.trackingLastUpdatedAt,
    this.currentEtaMinutes,
    this.currentDistanceKm,
    this.trackingStatus = 'IDLE',
    this.isRematched = false,
    this.rematchCount = 0,
    this.rematchReason,
    this.previousVolunteerId,
    this.previousVolunteerName,
    this.safetyCheckCompleted = false,
    this.safetyCheckStatus = 'PASSED',
    this.safetyCheckVersion,
    this.safetyCheckAnswers,
    this.pickupMode = 'volunteer_dispatch',
  });

  factory DonationModel.fromJson(Map<String, dynamic> json) {
    var historyList = <DonationHistoryModel>[];
    if (json['history'] != null) {
      historyList = (json['history'] as List)
          .map((h) => DonationHistoryModel.fromJson(h))
          .toList();
    }

    FoodRescueWindowModel? rescueWindowObj;
    if (json['rescue_window'] != null && json['rescue_window'] is Map<String, dynamic>) {
      rescueWindowObj = FoodRescueWindowModel.fromJson(json['rescue_window']);
    }

    RescueFeasibilityModel? feasibilityObj;
    if (json['feasibility'] != null && json['feasibility'] is Map<String, dynamic>) {
      feasibilityObj = RescueFeasibilityModel.fromJson(json['feasibility']);
    }

    return DonationModel(
      id: json['id'],
      donorId: json['donor_id'],
      foodName: json['food_name'] ?? '',
      foodType: json['food_type'],
      foodSource: json['food_source'] ?? 'KNOWN',
      customFoodName: json['custom_food_name'],
      foodDescription: json['food_description'],
      majorIngredients: json['major_ingredients'],
      description: json['description'],
      foodCategory: json['food_category'] ?? 'Other',
      quantity: (json['quantity'] as num).toDouble(),
      quantityUnit: json['quantity_unit'] ?? 'Meals',
      quantityUnitLabel: json['quantity_unit_label'],
      estimatedMeals: json['estimated_meals'] != null ? (json['estimated_meals'] as num).toDouble() : null,
      ruleCoverage: json['rule_coverage'] ?? 'HIGH',
      classificationSource: json['classification_source'] ?? 'rule_exact',
      classificationConfidence: json['classification_confidence'] != null ? (json['classification_confidence'] as num).toDouble() : 1.0,
      preparationTime: json['preparation_time'] ?? '',
      expiryTime: json['expiry_time'] ?? '',
      pickupAddress: json['pickup_address'] ?? '',
      latitude: json['latitude'] != null ? (json['latitude'] as num).toDouble() : null,
      longitude: json['longitude'] != null ? (json['longitude'] as num).toDouble() : null,
      imageUrl: json['image_url'],
      storageMethod: json['storage_method'],
      storageDurationHours: json['storage_duration_hours'] != null ? (json['storage_duration_hours'] as num).toDouble() : null,
      storageContinuous: json['storage_continuous'] ?? true,
      storageHistoryJson: json['storage_history_json'],
      packagingCondition: json['packaging_condition'],
      previouslyServed: json['previously_served'] ?? 'No',
      exposureStatus: json['exposure_status'] ?? 'No',
      handlingStatus: json['handling_status'] ?? 'No',
      pickupDeadline: json['pickup_deadline'],
      estimatedWindowStart: json['estimated_window_start'],
      estimatedWindowEnd: json['estimated_window_end'],
      remainingMinutes: json['remaining_minutes'],
      rescueUrgencyLevel: json['rescue_urgency_level'] ?? 'FRESH',
      feasibilityStatus: json['feasibility_status'] ?? 'RESCUE_FEASIBLE',
      reasonsJson: json['reasons_json'],
      aiFoodDetected: json['ai_food_detected'],
      aiVisibleSpoilage: json['ai_visible_spoilage'],
      aiDiscoloration: json['ai_discoloration'],
      aiPackagingIntact: json['ai_packaging_intact'],
      aiVisualCondition: json['ai_visual_condition'],
      aiConfidenceScore: json['ai_confidence_score'] != null ? (json['ai_confidence_score'] as num).toDouble() : null,
      conditionScore: json['condition_score'],
      verificationOtp: json['verification_otp'],
      qrCodeToken: json['qr_code_token'],
      isEmergency: json['is_emergency'] ?? false,
      failureReason: json['failure_reason'],
      status: json['status'] ?? 'pending',
      assignedNgoId: json['assigned_ngo_id'],
      assignedVolunteerId: json['assigned_volunteer_id'],
      pickupMode: json['pickup_mode'] ?? 'volunteer_dispatch',
      createdAt: json['created_at'] ?? '',
      urgencyLevel: json['urgency_level'] ?? 'Fresh',
      donorName: json['donor_name'],
      donorPhone: json['donor_phone'],
      ngoName: json['ngo_name'],
      volunteerName: json['volunteer_name'],
      volunteerPhone: json['volunteer_phone'],
      rescueWindow: rescueWindowObj,
      feasibility: feasibilityObj,
      history: historyList,
      trackingLatitude: (json['tracking_latitude'] as num?)?.toDouble(),
      trackingLongitude: (json['tracking_longitude'] as num?)?.toDouble(),
      trackingLastUpdatedAt: json['tracking_last_updated_at'],
      currentEtaMinutes: (json['current_eta_minutes'] as num?)?.toDouble(),
      currentDistanceKm: (json['current_distance_km'] as num?)?.toDouble(),
      trackingStatus: json['tracking_status'] ?? 'IDLE',
      isRematched: json['is_rematched'] ?? false,
      rematchCount: json['rematch_count'] ?? 0,
      rematchReason: json['rematch_reason'],
      previousVolunteerId: json['previous_volunteer_id'],
      previousVolunteerName: json['previous_volunteer_name'],
      safetyCheckCompleted: json['safety_check_completed'] ?? false,
      safetyCheckStatus: json['safety_check_status'] ?? 'PASSED',
      safetyCheckVersion: json['safety_check_version'],
      safetyCheckAnswers: json['safety_check_answers'] is Map<String, dynamic> ? json['safety_check_answers'] : null,
    );
  }

  String get pickupLocation => pickupAddress;

  String get timeRemainingFormatted {
    final mins = remainingMinutes ?? rescueWindow?.remainingMinutes ?? 0;
    if (mins <= 0) return 'Ended';
    if (mins < 60) return '$mins min remaining';
    final hrs = mins ~/ 60;
    final rMins = mins % 60;
    return '${hrs}h ${rMins}m remaining';
  }
}

class DonorCustomFoodProfileModel {
  final int id;
  final int donorId;
  final String name;
  final String foodCategory;
  final String? description;
  final String? majorIngredients;
  final String commonStorage;
  final String defaultUnit;
  final int usageCount;
  final String createdAt;

  DonorCustomFoodProfileModel({
    required this.id,
    required this.donorId,
    required this.name,
    required this.foodCategory,
    this.description,
    this.majorIngredients,
    this.commonStorage = 'Room Temperature',
    this.defaultUnit = 'Meals',
    this.usageCount = 1,
    required this.createdAt,
  });

  factory DonorCustomFoodProfileModel.fromJson(Map<String, dynamic> json) {
    return DonorCustomFoodProfileModel(
      id: json['id'],
      donorId: json['donor_id'],
      name: json['name'] ?? '',
      foodCategory: json['food_category'] ?? 'Cooked Food',
      description: json['description'],
      majorIngredients: json['major_ingredients'],
      commonStorage: json['common_storage'] ?? 'Room Temperature',
      defaultUnit: json['default_unit'] ?? 'Meals',
      usageCount: json['usage_count'] ?? 1,
      createdAt: json['created_at'] ?? '',
    );
  }
}

class RescueClaimPreviewModel {
  final String claimToken;
  final int donationId;
  final String foodName;
  final String foodCategory;
  final double quantity;
  final String quantityUnit;
  final String pickupNeighborhood;
  final double? approxLatitude;
  final double? approxLongitude;
  final int remainingMinutes;
  final String urgencyLevel;
  final bool isFeasible;
  final String expiresAt;
  final String status;
  final String? dietaryType;

  RescueClaimPreviewModel({
    required this.claimToken,
    required this.donationId,
    required this.foodName,
    required this.foodCategory,
    required this.quantity,
    required this.quantityUnit,
    required this.pickupNeighborhood,
    this.approxLatitude,
    this.approxLongitude,
    required this.remainingMinutes,
    required this.urgencyLevel,
    this.isFeasible = true,
    required this.expiresAt,
    required this.status,
    this.dietaryType,
  });

  factory RescueClaimPreviewModel.fromJson(Map<String, dynamic> json) {
    return RescueClaimPreviewModel(
      claimToken: json['claim_token'] ?? '',
      donationId: json['donation_id'] ?? 0,
      foodName: json['food_name'] ?? 'Prepared Food',
      foodCategory: json['food_category'] ?? 'Cooked Food',
      quantity: (json['quantity'] as num?)?.toDouble() ?? 0.0,
      quantityUnit: json['quantity_unit'] ?? 'Meals',
      pickupNeighborhood: json['pickup_neighborhood'] ?? 'Nearby area',
      approxLatitude: (json['approx_latitude'] as num?)?.toDouble(),
      approxLongitude: (json['approx_longitude'] as num?)?.toDouble(),
      remainingMinutes: json['remaining_minutes'] ?? 60,
      urgencyLevel: json['urgency_level'] ?? 'URGENT',
      isFeasible: json['is_feasible'] ?? true,
      expiresAt: json['expires_at'] ?? '',
      status: json['status'] ?? 'pending',
      dietaryType: json['dietary_type'],
    );
  }
}

class RescueClaimAcceptResult {
  final String accessToken;
  final String tokenType;
  final Map<String, dynamic> user;
  final int assignmentId;
  final int donationId;
  final String status;
  final String pickupAddress;
  final double? currentEtaMinutes;
  final int remainingMinutes;
  final String urgencyLevel;
  final String message;

  RescueClaimAcceptResult({
    required this.accessToken,
    this.tokenType = 'bearer',
    required this.user,
    required this.assignmentId,
    required this.donationId,
    required this.status,
    required this.pickupAddress,
    this.currentEtaMinutes,
    required this.remainingMinutes,
    required this.urgencyLevel,
    required this.message,
  });

  factory RescueClaimAcceptResult.fromJson(Map<String, dynamic> json) {
    return RescueClaimAcceptResult(
      accessToken: json['access_token'] ?? '',
      tokenType: json['token_type'] ?? 'bearer',
      user: json['user'] is Map ? Map<String, dynamic>.from(json['user']) : {},
      assignmentId: json['assignment_id'] ?? 0,
      donationId: json['donation_id'] ?? 0,
      status: json['status'] ?? 'volunteer_assigned',
      pickupAddress: json['pickup_address'] ?? '',
      currentEtaMinutes: (json['current_eta_minutes'] as num?)?.toDouble(),
      remainingMinutes: json['remaining_minutes'] ?? 0,
      urgencyLevel: json['urgency_level'] ?? 'URGENT',
      message: json['message'] ?? '',
    );
  }
}
