class RatingModel {
  final int id;
  final int donationId;
  final int fromUserId;
  final int toUserId;
  final String roleFrom;
  final String roleTo;
  final int ratingScore;
  final String? feedback;
  final String? tags;
  final String createdAt;

  RatingModel({
    required this.id,
    required this.donationId,
    required this.fromUserId,
    required this.toUserId,
    required this.roleFrom,
    required this.roleTo,
    required this.ratingScore,
    this.feedback,
    this.tags,
    required this.createdAt,
  });

  factory RatingModel.fromJson(Map<String, dynamic> json) {
    return RatingModel(
      id: json['id'],
      donationId: json['donation_id'],
      fromUserId: json['from_user_id'],
      toUserId: json['to_user_id'],
      roleFrom: json['role_from'] ?? '',
      roleTo: json['role_to'] ?? '',
      ratingScore: json['rating_score'] ?? 5,
      feedback: json['feedback'],
      tags: json['tags'],
      createdAt: json['created_at'] ?? '',
    );
  }
}
