class RewardModel {
  final int id;
  final int userId;
  final int points;
  final String level;
  final int nextLevelPoints;
  final int pointsToNextLevel;

  RewardModel({
    required this.id,
    required this.userId,
    required this.points,
    required this.level,
    required this.nextLevelPoints,
    required this.pointsToNextLevel,
  });

  factory RewardModel.fromJson(Map<String, dynamic> json) {
    return RewardModel(
      id: json['id'],
      userId: json['user_id'],
      points: json['points'] ?? 0,
      level: json['level'] ?? 'Bronze',
      nextLevelPoints: json['next_level_points'] ?? 100,
      pointsToNextLevel: json['points_to_next_level'] ?? 100,
    );
  }
}
