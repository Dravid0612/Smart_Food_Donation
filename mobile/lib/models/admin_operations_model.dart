class AdminReceivingSummaryModel {
  final int activeRescues;
  final int urgentRescues;
  final int criticalRescues;
  final int inTransit;
  final double receivedToday;
  final double distributedToday;
  final double remainingToday;
  final int issuesOpen;
  final double foodAtRiskMeals;
  final int completedToday;

  AdminReceivingSummaryModel({
    required this.activeRescues,
    required this.urgentRescues,
    required this.criticalRescues,
    required this.inTransit,
    required this.receivedToday,
    required this.distributedToday,
    required this.remainingToday,
    required this.issuesOpen,
    required this.foodAtRiskMeals,
    required this.completedToday,
  });

  factory AdminReceivingSummaryModel.fromJson(Map<String, dynamic> json) {
    return AdminReceivingSummaryModel(
      activeRescues: json['active_rescues'] ?? 0,
      urgentRescues: json['urgent_rescues'] ?? 0,
      criticalRescues: json['critical_rescues'] ?? 0,
      inTransit: json['in_transit'] ?? 0,
      receivedToday: (json['received_today'] as num?)?.toDouble() ?? 0.0,
      distributedToday: (json['distributed_today'] as num?)?.toDouble() ?? 0.0,
      remainingToday: (json['remaining_today'] as num?)?.toDouble() ?? 0.0,
      issuesOpen: json['issues_open'] ?? 0,
      foodAtRiskMeals: (json['food_at_risk_meals'] as num?)?.toDouble() ?? 0.0,
      completedToday: json['completed_today'] ?? 0,
    );
  }
}

class AdminReceivingItemModel {
  final int id;
  final String foodName;
  final String foodCategory;
  final double quantity;
  final String quantityUnit;
  final int donorId;
  final String? donorName;
  final String? donorPhone;
  final int? assignedNgoId;
  final String? ngoName;
  final int? assignedVolunteerId;
  final String? volunteerName;
  final String? volunteerPhone;
  final String status;
  final String rescueUrgencyLevel;
  final int? remainingMinutes;
  final String aiVisualCondition;
  final String storageMethod;
  final String packagingCondition;
  final double? etaMinutes;
  final double expectedQuantity;
  final double? receivedQuantity;
  final bool hasQuantityMismatch;
  final double? discrepancyAmount;
  final String? discrepancyReason;
  final double? distributedQuantity;
  final double? remainingQuantity;
  final int issueCount;
  final String pickupAddress;
  final String createdAt;
  final String? acceptedAt;
  final String? collectedAt;
  final String? deliveredAt;
  final String? completedAt;

  AdminReceivingItemModel({
    required this.id,
    required this.foodName,
    required this.foodCategory,
    required this.quantity,
    required this.quantityUnit,
    required this.donorId,
    this.donorName,
    this.donorPhone,
    this.assignedNgoId,
    this.ngoName,
    this.assignedVolunteerId,
    this.volunteerName,
    this.volunteerPhone,
    required this.status,
    required this.rescueUrgencyLevel,
    this.remainingMinutes,
    this.aiVisualCondition = 'GOOD',
    this.storageMethod = 'Room Temperature',
    this.packagingCondition = 'Sealed / Covered',
    this.etaMinutes,
    required this.expectedQuantity,
    this.receivedQuantity,
    this.hasQuantityMismatch = false,
    this.discrepancyAmount,
    this.discrepancyReason,
    this.distributedQuantity,
    this.remainingQuantity,
    this.issueCount = 0,
    required this.pickupAddress,
    required this.createdAt,
    this.acceptedAt,
    this.collectedAt,
    this.deliveredAt,
    this.completedAt,
  });

  factory AdminReceivingItemModel.fromJson(Map<String, dynamic> json) {
    return AdminReceivingItemModel(
      id: json['id'],
      foodName: json['food_name'] ?? '',
      foodCategory: json['food_category'] ?? 'Cooked Food',
      quantity: (json['quantity'] as num).toDouble(),
      quantityUnit: json['quantity_unit'] ?? 'Meals',
      donorId: json['donor_id'] ?? 0,
      donorName: json['donor_name'],
      donorPhone: json['donor_phone'],
      assignedNgoId: json['assigned_ngo_id'],
      ngoName: json['ngo_name'],
      assignedVolunteerId: json['assigned_volunteer_id'],
      volunteerName: json['volunteer_name'],
      volunteerPhone: json['volunteer_phone'],
      status: json['status'] ?? 'pending',
      rescueUrgencyLevel: json['rescue_urgency_level'] ?? 'FRESH',
      remainingMinutes: json['remaining_minutes'],
      aiVisualCondition: json['ai_visual_condition'] ?? 'GOOD',
      storageMethod: json['storage_method'] ?? 'Room Temperature',
      packagingCondition: json['packaging_condition'] ?? 'Sealed / Covered',
      etaMinutes: (json['eta_minutes'] as num?)?.toDouble(),
      expectedQuantity: (json['expected_quantity'] as num?)?.toDouble() ?? (json['quantity'] as num).toDouble(),
      receivedQuantity: (json['received_quantity'] as num?)?.toDouble(),
      hasQuantityMismatch: json['has_quantity_mismatch'] ?? false,
      discrepancyAmount: (json['discrepancy_amount'] as num?)?.toDouble(),
      discrepancyReason: json['discrepancy_reason'],
      distributedQuantity: (json['distributed_quantity'] as num?)?.toDouble(),
      remainingQuantity: (json['remaining_quantity'] as num?)?.toDouble(),
      issueCount: json['issue_count'] ?? 0,
      pickupAddress: json['pickup_address'] ?? '',
      createdAt: json['created_at'] ?? '',
      acceptedAt: json['accepted_at'],
      collectedAt: json['collected_at'],
      deliveredAt: json['delivered_at'],
      completedAt: json['completed_at'],
    );
  }
}

class AdminRescueTimelineItemModel {
  final String stage;
  final String label;
  final String? timestamp;
  final bool isCompleted;
  final bool isCurrent;
  final String? actorName;
  final String? details;

  AdminRescueTimelineItemModel({
    required this.stage,
    required this.label,
    this.timestamp,
    required this.isCompleted,
    required this.isCurrent,
    this.actorName,
    this.details,
  });

  factory AdminRescueTimelineItemModel.fromJson(Map<String, dynamic> json) {
    return AdminRescueTimelineItemModel(
      stage: json['stage'] ?? '',
      label: json['label'] ?? '',
      timestamp: json['timestamp'],
      isCompleted: json['is_completed'] ?? false,
      isCurrent: json['is_current'] ?? false,
      actorName: json['actor_name'],
      details: json['details'],
    );
  }
}

class AdminRescueDetailModel extends AdminReceivingItemModel {
  final List<AdminRescueTimelineItemModel> timeline;
  final bool ngoCapacityAvailable;
  final double? ngoCurrentCapacity;
  final double? ngoMaxCapacity;

  AdminRescueDetailModel({
    required super.id,
    required super.foodName,
    required super.foodCategory,
    required super.quantity,
    required super.quantityUnit,
    required super.donorId,
    super.donorName,
    super.donorPhone,
    super.assignedNgoId,
    super.ngoName,
    super.assignedVolunteerId,
    super.volunteerName,
    super.volunteerPhone,
    required super.status,
    required super.rescueUrgencyLevel,
    super.remainingMinutes,
    super.aiVisualCondition,
    super.storageMethod,
    super.packagingCondition,
    super.etaMinutes,
    required super.expectedQuantity,
    super.receivedQuantity,
    super.hasQuantityMismatch,
    super.discrepancyAmount,
    super.discrepancyReason,
    super.distributedQuantity,
    super.remainingQuantity,
    super.issueCount,
    required super.pickupAddress,
    required super.createdAt,
    super.acceptedAt,
    super.collectedAt,
    super.deliveredAt,
    super.completedAt,
    this.timeline = const [],
    this.ngoCapacityAvailable = true,
    this.ngoCurrentCapacity,
    this.ngoMaxCapacity,
    this.preparationTime,
    this.aiAdvisory,
    this.currentWave = 1,
    this.waveName,
    this.offersCount = 0,
    this.feasibilityStatus = 'FEASIBLE',
    this.otpState = 'NOT_GENERATED',
    this.pickupMode = 'volunteer_dispatch',
    this.blockedReason,
    this.hasClaimToken = false,
    this.claimToken,
    this.mealsRescued = 0.0,
    this.environmentalCo2Kg = 0.0,
    this.environmentalWaterLiters = 0.0,
  });

  final String? preparationTime;
  final String? aiAdvisory;
  final int currentWave;
  final String? waveName;
  final int offersCount;
  final String feasibilityStatus;
  final String otpState; // Strictly state string, never plaintext OTP
  final String pickupMode;
  final String? blockedReason;
  final bool hasClaimToken;
  final String? claimToken;
  final double mealsRescued;
  final double environmentalCo2Kg;
  final double environmentalWaterLiters;

  factory AdminRescueDetailModel.fromJson(Map<String, dynamic> json) {
    var baseItem = AdminReceivingItemModel.fromJson(json);
    var timelineList = <AdminRescueTimelineItemModel>[];
    if (json['timeline'] != null && json['timeline'] is List) {
      timelineList = (json['timeline'] as List)
          .map((t) => AdminRescueTimelineItemModel.fromJson(t))
          .toList();
    }

    return AdminRescueDetailModel(
      id: baseItem.id,
      foodName: baseItem.foodName,
      foodCategory: baseItem.foodCategory,
      quantity: baseItem.quantity,
      quantityUnit: baseItem.quantityUnit,
      donorId: baseItem.donorId,
      donorName: baseItem.donorName,
      donorPhone: baseItem.donorPhone,
      assignedNgoId: baseItem.assignedNgoId,
      ngoName: baseItem.ngoName,
      assignedVolunteerId: baseItem.assignedVolunteerId,
      volunteerName: baseItem.volunteerName,
      volunteerPhone: baseItem.volunteerPhone,
      status: baseItem.status,
      rescueUrgencyLevel: baseItem.rescueUrgencyLevel,
      remainingMinutes: baseItem.remainingMinutes,
      aiVisualCondition: baseItem.aiVisualCondition,
      storageMethod: baseItem.storageMethod,
      packagingCondition: baseItem.packagingCondition,
      etaMinutes: baseItem.etaMinutes,
      expectedQuantity: baseItem.expectedQuantity,
      receivedQuantity: baseItem.receivedQuantity,
      hasQuantityMismatch: baseItem.hasQuantityMismatch,
      discrepancyAmount: baseItem.discrepancyAmount,
      discrepancyReason: baseItem.discrepancyReason,
      distributedQuantity: baseItem.distributedQuantity,
      remainingQuantity: baseItem.remainingQuantity,
      issueCount: baseItem.issueCount,
      pickupAddress: baseItem.pickupAddress,
      createdAt: baseItem.createdAt,
      acceptedAt: baseItem.acceptedAt,
      collectedAt: baseItem.collectedAt,
      deliveredAt: baseItem.deliveredAt,
      completedAt: baseItem.completedAt,
      timeline: timelineList,
      ngoCapacityAvailable: json['ngo_capacity_available'] ?? true,
      ngoCurrentCapacity: (json['ngo_current_capacity'] as num?)?.toDouble(),
      ngoMaxCapacity: (json['ngo_max_capacity'] as num?)?.toDouble(),
      preparationTime: json['preparation_time']?.toString(),
      aiAdvisory: json['ai_advisory']?.toString(),
      currentWave: json['current_wave'] ?? 1,
      waveName: json['wave_name']?.toString(),
      offersCount: json['offers_count'] ?? 0,
      feasibilityStatus: json['feasibility_status'] ?? 'FEASIBLE',
      otpState: json['otp_state'] ?? 'NOT_GENERATED',
      pickupMode: json['pickup_mode'] ?? 'volunteer_dispatch',
      blockedReason: json['blocked_reason']?.toString(),
      hasClaimToken: json['has_claim_token'] ?? false,
      claimToken: json['claim_token']?.toString(),
      mealsRescued: (json['meals_rescued'] as num?)?.toDouble() ?? 0.0,
      environmentalCo2Kg: (json['environmental_co2_kg'] as num?)?.toDouble() ?? 0.0,
      environmentalWaterLiters: (json['environmental_water_liters'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class AdminNgoCapacityModel {
  final int id;
  final String organizationName;
  final String address;
  final double currentCapacity;
  final double maxCapacity;
  final double remainingCapacity;
  final double utilizationPercent;
  final bool isVerified;
  final bool isOpen;
  final String statusColor;

  AdminNgoCapacityModel({
    required this.id,
    required this.organizationName,
    required this.address,
    required this.currentCapacity,
    required this.maxCapacity,
    required this.remainingCapacity,
    required this.utilizationPercent,
    required this.isVerified,
    required this.isOpen,
    required this.statusColor,
  });

  factory AdminNgoCapacityModel.fromJson(Map<String, dynamic> json) {
    return AdminNgoCapacityModel(
      id: json['id'],
      organizationName: json['organization_name'] ?? '',
      address: json['address'] ?? '',
      currentCapacity: (json['current_capacity'] as num?)?.toDouble() ?? 0.0,
      maxCapacity: (json['max_capacity'] as num?)?.toDouble() ?? 500.0,
      remainingCapacity: (json['remaining_capacity'] as num?)?.toDouble() ?? 500.0,
      utilizationPercent: (json['utilization_percent'] as num?)?.toDouble() ?? 0.0,
      isVerified: json['is_verified'] ?? false,
      isOpen: json['is_open'] ?? true,
      statusColor: json['status_color'] ?? 'GREEN',
    );
  }
}

class AdminCategoryBreakdownItemModel {
  final String category;
  final int count;
  final double totalMeals;
  final double percentage;

  AdminCategoryBreakdownItemModel({
    required this.category,
    required this.count,
    required this.totalMeals,
    required this.percentage,
  });

  factory AdminCategoryBreakdownItemModel.fromJson(Map<String, dynamic> json) {
    return AdminCategoryBreakdownItemModel(
      category: json['category'] ?? '',
      count: json['count'] ?? 0,
      totalMeals: (json['total_meals'] as num?)?.toDouble() ?? 0.0,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class AdminMonthlyReportModel {
  final String month;
  final int donationsCount;
  final double foodRecoveredKg;
  final double mealsRescued;
  final double receivedQuantity;
  final double distributedQuantity;
  final int completedRescues;
  final double estimatedCo2eKg;
  final double estimatedWaterLiters;
  final double estimatedDisposalCostAvoidedInr;
  final double avgRescueCompletionMinutes;
  final bool isEstimated;

  AdminMonthlyReportModel({
    required this.month,
    required this.donationsCount,
    required this.foodRecoveredKg,
    required this.mealsRescued,
    required this.receivedQuantity,
    required this.distributedQuantity,
    required this.completedRescues,
    required this.estimatedCo2eKg,
    required this.estimatedWaterLiters,
    required this.estimatedDisposalCostAvoidedInr,
    required this.avgRescueCompletionMinutes,
    this.isEstimated = true,
  });

  factory AdminMonthlyReportModel.fromJson(Map<String, dynamic> json) {
    return AdminMonthlyReportModel(
      month: json['month'] ?? '',
      donationsCount: json['donations_count'] ?? 0,
      foodRecoveredKg: (json['food_recovered_kg'] as num?)?.toDouble() ?? 0.0,
      mealsRescued: (json['meals_rescued'] as num?)?.toDouble() ?? 0.0,
      receivedQuantity: (json['received_quantity'] as num?)?.toDouble() ?? 0.0,
      distributedQuantity: (json['distributed_quantity'] as num?)?.toDouble() ?? 0.0,
      completedRescues: json['completed_rescues'] ?? 0,
      estimatedCo2eKg: (json['estimated_co2e_kg'] as num?)?.toDouble() ?? 0.0,
      estimatedWaterLiters: (json['estimated_water_liters'] as num?)?.toDouble() ?? 0.0,
      estimatedDisposalCostAvoidedInr: (json['estimated_disposal_cost_avoided_inr'] as num?)?.toDouble() ?? 0.0,
      avgRescueCompletionMinutes: (json['avg_rescue_completion_minutes'] as num?)?.toDouble() ?? 0.0,
      isEstimated: json['is_estimated'] ?? true,
    );
  }
}

class AdminRepeatDonorPatternItemModel {
  final String dayOfWeek;
  final String foodCategory;
  final int donationCount;
  final double avgSurplus;
  final double avgRescued;
  final double avgUnrescued;
  final List<String> topDonors;

  AdminRepeatDonorPatternItemModel({
    required this.dayOfWeek,
    required this.foodCategory,
    required this.donationCount,
    required this.avgSurplus,
    required this.avgRescued,
    required this.avgUnrescued,
    this.topDonors = const [],
  });

  factory AdminRepeatDonorPatternItemModel.fromJson(Map<String, dynamic> json) {
    return AdminRepeatDonorPatternItemModel(
      dayOfWeek: json['day_of_week'] ?? '',
      foodCategory: json['food_category'] ?? '',
      donationCount: json['donation_count'] ?? 0,
      avgSurplus: (json['avg_surplus'] as num?)?.toDouble() ?? 0.0,
      avgRescued: (json['avg_rescued'] as num?)?.toDouble() ?? 0.0,
      avgUnrescued: (json['avg_unrescued'] as num?)?.toDouble() ?? 0.0,
      topDonors: (json['top_donors'] as List?)?.map((e) => e.toString()).toList() ?? [],
    );
  }
}

class AdminRepeatDonorInsightsModel {
  final int totalDonationsAnalyzed;
  final List<AdminRepeatDonorPatternItemModel> patterns;

  AdminRepeatDonorInsightsModel({
    required this.totalDonationsAnalyzed,
    required this.patterns,
  });

  factory AdminRepeatDonorInsightsModel.fromJson(Map<String, dynamic> json) {
    return AdminRepeatDonorInsightsModel(
      totalDonationsAnalyzed: json['total_donations_analyzed'] ?? 0,
      patterns: (json['patterns'] as List?)
              ?.map((e) => AdminRepeatDonorPatternItemModel.fromJson(e))
              .toList() ??
          [],
    );
  }
}
