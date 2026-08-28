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
  });

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
