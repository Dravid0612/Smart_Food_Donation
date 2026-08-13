class NgoRecommendationModel {
  final int ngoId;
  final String organizationName;
  final double distanceKm;
  final double score;
  final String reason;
  final int capacity;
  final int currentCapacity;
  final bool isAvailable;

  NgoRecommendationModel({
    required this.ngoId,
    required this.organizationName,
    required this.distanceKm,
    required this.score,
    required this.reason,
    required this.capacity,
    required this.currentCapacity,
    required this.isAvailable,
  });

  factory NgoRecommendationModel.fromJson(Map<String, dynamic> json) {
    return NgoRecommendationModel(
      ngoId: json['ngo_id'],
      organizationName: json['organization_name'] ?? '',
      distanceKm: (json['distance_km'] as num).toDouble(),
      score: (json['score'] as num).toDouble(),
      reason: json['reason'] ?? '',
      capacity: json['capacity'] ?? 0,
      currentCapacity: json['current_capacity'] ?? 0,
      isAvailable: json['is_available'] ?? true,
    );
  }
}

class VolunteerRecommendationModel {
  final int volunteerId;
  final String volunteerName;
  final String? phone;
  final double distanceKm;
  final double score;
  final String reason;

  VolunteerRecommendationModel({
    required this.volunteerId,
    required this.volunteerName,
    this.phone,
    required this.distanceKm,
    required this.score,
    required this.reason,
  });

  factory VolunteerRecommendationModel.fromJson(Map<String, dynamic> json) {
    return VolunteerRecommendationModel(
      volunteerId: json['volunteer_id'],
      volunteerName: json['volunteer_name'] ?? '',
      phone: json['phone'],
      distanceKm: (json['distance_km'] as num).toDouble(),
      score: (json['score'] as num).toDouble(),
      reason: json['reason'] ?? '',
    );
  }
}
