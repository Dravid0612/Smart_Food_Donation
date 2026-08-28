class RawOperationalMetrics {
  final int totalTasksAssigned;
  final int totalTasksAccepted;
  final int totalCompleted;
  final int totalCancelled;
  final int totalNoShows;
  final int totalOnTime;
  final int totalDelayed;
  final int totalFeedbacksReceived;
  final double averageResponseTimeSeconds;

  RawOperationalMetrics({
    required this.totalTasksAssigned,
    required this.totalTasksAccepted,
    required this.totalCompleted,
    required this.totalCancelled,
    required this.totalNoShows,
    required this.totalOnTime,
    required this.totalDelayed,
    required this.totalFeedbacksReceived,
    required this.averageResponseTimeSeconds,
  });

  factory RawOperationalMetrics.fromJson(Map<String, dynamic> json) {
    return RawOperationalMetrics(
      totalTasksAssigned: json['total_tasks_assigned'] ?? 0,
      totalTasksAccepted: json['total_tasks_accepted'] ?? 0,
      totalCompleted: json['total_completed'] ?? 0,
      totalCancelled: json['total_cancelled'] ?? 0,
      totalNoShows: json['total_no_shows'] ?? 0,
      totalOnTime: json['total_on_time'] ?? 0,
      totalDelayed: json['total_delayed'] ?? 0,
      totalFeedbacksReceived: json['total_feedbacks_received'] ?? 0,
      averageResponseTimeSeconds: (json['average_response_time_seconds'] as num?)?.toDouble() ?? 180.0,
    );
  }
}

class DerivedReliabilityMetrics {
  final double completionRatePercent;
  final double onTimeRatePercent;
  final double cancellationRatePercent;
  final double noShowRatePercent;
  final double serviceQualityScorePercent;
  final double responseSpeedScorePercent;

  DerivedReliabilityMetrics({
    required this.completionRatePercent,
    required this.onTimeRatePercent,
    required this.cancellationRatePercent,
    required this.noShowRatePercent,
    required this.serviceQualityScorePercent,
    required this.responseSpeedScorePercent,
  });

  factory DerivedReliabilityMetrics.fromJson(Map<String, dynamic> json) {
    return DerivedReliabilityMetrics(
      completionRatePercent: (json['completion_rate_percent'] as num?)?.toDouble() ?? 100.0,
      onTimeRatePercent: (json['on_time_rate_percent'] as num?)?.toDouble() ?? 100.0,
      cancellationRatePercent: (json['cancellation_rate_percent'] as num?)?.toDouble() ?? 0.0,
      noShowRatePercent: (json['no_show_rate_percent'] as num?)?.toDouble() ?? 0.0,
      serviceQualityScorePercent: (json['service_quality_score_percent'] as num?)?.toDouble() ?? 100.0,
      responseSpeedScorePercent: (json['response_speed_score_percent'] as num?)?.toDouble() ?? 90.0,
    );
  }
}

class PerformanceDimension {
  final String name;
  final double score;
  final double weight;
  final String description;

  PerformanceDimension({
    required this.name,
    required this.score,
    required this.weight,
    required this.description,
  });

  factory PerformanceDimension.fromJson(Map<String, dynamic> json) {
    return PerformanceDimension(
      name: json['name'] ?? '',
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      weight: (json['weight'] as num?)?.toDouble() ?? 0.0,
      description: json['description'] ?? '',
    );
  }
}

class MatchReasonItem {
  final String code;
  final String label;
  final bool isPositive;

  MatchReasonItem({
    required this.code,
    required this.label,
    required this.isPositive,
  });

  factory MatchReasonItem.fromJson(Map<String, dynamic> json) {
    return MatchReasonItem(
      code: json['code'] ?? '',
      label: json['label'] ?? '',
      isPositive: json['is_positive'] ?? true,
    );
  }
}

class PerformanceProfile {
  final int userId;
  final String name;
  final String role;
  final String performanceStatus;
  final String adminActionStatus;
  final String? adminActionNotes;
  final double overallReliabilityScore;
  final String trustTier;
  final List<String> trustBadges;
  final String recentTrend;
  final String trendDescription;
  final bool hasSufficientHistory;
  final int sampleSizeThreshold;
  final int recencyWindowSize;
  final RawOperationalMetrics rawMetrics;
  final DerivedReliabilityMetrics derivedMetrics;
  final List<PerformanceDimension> dimensions;

  PerformanceProfile({
    required this.userId,
    required this.name,
    required this.role,
    required this.performanceStatus,
    required this.adminActionStatus,
    this.adminActionNotes,
    required this.overallReliabilityScore,
    required this.trustTier,
    required this.trustBadges,
    required this.recentTrend,
    required this.trendDescription,
    required this.hasSufficientHistory,
    required this.sampleSizeThreshold,
    required this.recencyWindowSize,
    required this.rawMetrics,
    required this.derivedMetrics,
    required this.dimensions,
  });

  factory PerformanceProfile.fromJson(Map<String, dynamic> json) {
    return PerformanceProfile(
      userId: json['user_id'] ?? 0,
      name: json['name'] ?? '',
      role: json['role'] ?? 'volunteer',
      performanceStatus: json['performance_status'] ?? 'NEW',
      adminActionStatus: json['admin_action_status'] ?? 'NORMAL',
      adminActionNotes: json['admin_action_notes'],
      overallReliabilityScore: (json['overall_reliability_score'] as num?)?.toDouble() ?? 95.0,
      trustTier: json['trust_tier'] ?? 'New Member',
      trustBadges: List<String>.from(json['trust_badges'] ?? []),
      recentTrend: json['recent_trend'] ?? 'steady',
      trendDescription: json['trend_description'] ?? '',
      hasSufficientHistory: json['has_sufficient_history'] ?? false,
      sampleSizeThreshold: json['sample_size_threshold'] ?? 3,
      recencyWindowSize: json['recency_window_size'] ?? 10,
      rawMetrics: RawOperationalMetrics.fromJson(json['raw_metrics'] ?? {}),
      derivedMetrics: DerivedReliabilityMetrics.fromJson(json['derived_metrics'] ?? {}),
      dimensions: (json['dimensions'] as List<dynamic>? ?? [])
          .map((d) => PerformanceDimension.fromJson(d))
          .toList(),
    );
  }
}

class AdminPerformanceOverview {
  final int totalActiveVolunteers;
  final int totalVerifiedNgos;
  final double averagePickupTimeMinutes;
  final double averageVolunteerResponseTimeSeconds;
  final double volunteerAcceptanceRatePercent;
  final double networkOnTimeRatePercent;
  final double networkCompletionRatePercent;
  final double overallRescueSuccessRatePercent;
  final double fallbackEscalationRatePercent;
  final int needsReviewCount;
  final int criticalAlertsCount;

  AdminPerformanceOverview({
    required this.totalActiveVolunteers,
    required this.totalVerifiedNgos,
    required this.averagePickupTimeMinutes,
    required this.averageVolunteerResponseTimeSeconds,
    required this.volunteerAcceptanceRatePercent,
    required this.networkOnTimeRatePercent,
    required this.networkCompletionRatePercent,
    required this.overallRescueSuccessRatePercent,
    required this.fallbackEscalationRatePercent,
    required this.needsReviewCount,
    required this.criticalAlertsCount,
  });

  factory AdminPerformanceOverview.fromJson(Map<String, dynamic> json) {
    return AdminPerformanceOverview(
      totalActiveVolunteers: json['total_active_volunteers'] ?? 0,
      totalVerifiedNgos: json['total_verified_ngos'] ?? 0,
      averagePickupTimeMinutes: (json['average_pickup_time_minutes'] as num?)?.toDouble() ?? 0.0,
      averageVolunteerResponseTimeSeconds: (json['average_volunteer_response_time_seconds'] as num?)?.toDouble() ?? 0.0,
      volunteerAcceptanceRatePercent: (json['volunteer_acceptance_rate_percent'] as num?)?.toDouble() ?? 0.0,
      networkOnTimeRatePercent: (json['network_on_time_rate_percent'] as num?)?.toDouble() ?? 0.0,
      networkCompletionRatePercent: (json['network_completion_rate_percent'] as num?)?.toDouble() ?? 0.0,
      overallRescueSuccessRatePercent: (json['overall_rescue_success_rate_percent'] as num?)?.toDouble() ?? 0.0,
      fallbackEscalationRatePercent: (json['fallback_escalation_rate_percent'] as num?)?.toDouble() ?? 0.0,
      needsReviewCount: json['needs_review_count'] ?? 0,
      criticalAlertsCount: json['critical_alerts_count'] ?? 0,
    );
  }
}

class FailureReasonStat {
  final String reasonCode;
  final String reasonLabel;
  final int count;
  final double percentage;
  final String trend;

  FailureReasonStat({
    required this.reasonCode,
    required this.reasonLabel,
    required this.count,
    required this.percentage,
    required this.trend,
  });

  factory FailureReasonStat.fromJson(Map<String, dynamic> json) {
    return FailureReasonStat(
      reasonCode: json['reason_code'] ?? '',
      reasonLabel: json['reason_label'] ?? '',
      count: json['count'] ?? 0,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0.0,
      trend: json['trend'] ?? 'stable',
    );
  }
}

class RescueFailureAnalytics {
  final int totalRescueAttempts;
  final int totalCompletedRescues;
  final int totalFailedOrCancelled;
  final double rescueSuccessRatePercent;
  final List<FailureReasonStat> failureReasons;
  final String period;

  RescueFailureAnalytics({
    required this.totalRescueAttempts,
    required this.totalCompletedRescues,
    required this.totalFailedOrCancelled,
    required this.rescueSuccessRatePercent,
    required this.failureReasons,
    required this.period,
  });

  factory RescueFailureAnalytics.fromJson(Map<String, dynamic> json) {
    return RescueFailureAnalytics(
      totalRescueAttempts: json['total_rescue_attempts'] ?? 0,
      totalCompletedRescues: json['total_completed_rescues'] ?? 0,
      totalFailedOrCancelled: json['total_failed_or_cancelled'] ?? 0,
      rescueSuccessRatePercent: (json['rescue_success_rate_percent'] as num?)?.toDouble() ?? 0.0,
      failureReasons: (json['failure_reasons'] as List<dynamic>? ?? [])
          .map((f) => FailureReasonStat.fromJson(f))
          .toList(),
      period: json['period'] ?? 'all_time',
    );
  }
}

class NeedsReviewParticipant {
  final int userId;
  final String name;
  final String role;
  final String performanceStatus;
  final String adminActionStatus;
  final double overallReliabilityScore;
  final String triggerReason;
  final double noShowRatePercent;
  final double completionRatePercent;
  final double cancellationRatePercent;
  final int criticalIssuesCount;
  final int totalCompleted;
  final int totalAssigned;
  final String? adminNotes;
  final DateTime? lastActiveAt;

  NeedsReviewParticipant({
    required this.userId,
    required this.name,
    required this.role,
    required this.performanceStatus,
    required this.adminActionStatus,
    required this.overallReliabilityScore,
    required this.triggerReason,
    required this.noShowRatePercent,
    required this.completionRatePercent,
    required this.cancellationRatePercent,
    required this.criticalIssuesCount,
    required this.totalCompleted,
    required this.totalAssigned,
    this.adminNotes,
    this.lastActiveAt,
  });

  factory NeedsReviewParticipant.fromJson(Map<String, dynamic> json) {
    return NeedsReviewParticipant(
      userId: json['user_id'] ?? 0,
      name: json['name'] ?? '',
      role: json['role'] ?? '',
      performanceStatus: json['performance_status'] ?? 'NEEDS_REVIEW',
      adminActionStatus: json['admin_action_status'] ?? 'NORMAL',
      overallReliabilityScore: (json['overall_reliability_score'] as num?)?.toDouble() ?? 0.0,
      triggerReason: json['trigger_reason'] ?? '',
      noShowRatePercent: (json['no_show_rate_percent'] as num?)?.toDouble() ?? 0.0,
      completionRatePercent: (json['completion_rate_percent'] as num?)?.toDouble() ?? 0.0,
      cancellationRatePercent: (json['cancellation_rate_percent'] as num?)?.toDouble() ?? 0.0,
      criticalIssuesCount: json['critical_issues_count'] ?? 0,
      totalCompleted: json['total_completed'] ?? 0,
      totalAssigned: json['total_assigned'] ?? 0,
      adminNotes: json['admin_notes'],
      lastActiveAt: json['last_active_at'] != null ? DateTime.tryParse(json['last_active_at']) : null,
    );
  }
}

class SuspiciousFeedbackAlert {
  final int feedbackId;
  final int donationId;
  final int authorId;
  final String authorName;
  final String authorRole;
  final int? targetUserId;
  final String? targetName;
  final int rating;
  final String? comment;
  final String suspicionReason;
  final String severity;
  final DateTime createdAt;

  SuspiciousFeedbackAlert({
    required this.feedbackId,
    required this.donationId,
    required this.authorId,
    required this.authorName,
    required this.authorRole,
    this.targetUserId,
    this.targetName,
    required this.rating,
    this.comment,
    required this.suspicionReason,
    required this.severity,
    required this.createdAt,
  });

  factory SuspiciousFeedbackAlert.fromJson(Map<String, dynamic> json) {
    return SuspiciousFeedbackAlert(
      feedbackId: json['feedback_id'] ?? 0,
      donationId: json['donation_id'] ?? 0,
      authorId: json['author_id'] ?? 0,
      authorName: json['author_name'] ?? 'Unknown',
      authorRole: json['author_role'] ?? '',
      targetUserId: json['target_user_id'],
      targetName: json['target_name'],
      rating: json['rating'] ?? 5,
      comment: json['comment'],
      suspicionReason: json['suspicion_reason'] ?? 'burst',
      severity: json['severity'] ?? 'LOW',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}
