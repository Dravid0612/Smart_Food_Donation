class NgoModel {
  final int id;
  final int userId;
  final String organizationName;
  final String? description;
  final String? address;
  final double? latitude;
  final double? longitude;
  final int capacity;
  final int currentCapacity;
  final bool isAvailable;
  final bool isVerified;
  final String? contactPhone;

  NgoModel({
    required this.id,
    required this.userId,
    required this.organizationName,
    this.description,
    this.address,
    this.latitude,
    this.longitude,
    required this.capacity,
    required this.currentCapacity,
    required this.isAvailable,
    required this.isVerified,
    this.contactPhone,
  });

  factory NgoModel.fromJson(Map<String, dynamic> json) {
    return NgoModel(
      id: json['id'],
      userId: json['user_id'],
      organizationName: json['organization_name'] ?? '',
      description: json['description'],
      address: json['address'],
      latitude: json['latitude'] != null ? (json['latitude'] as num).toDouble() : null,
      longitude: json['longitude'] != null ? (json['longitude'] as num).toDouble() : null,
      capacity: json['capacity'] ?? 100,
      currentCapacity: json['current_capacity'] ?? 100,
      isAvailable: json['is_available'] ?? true,
      isVerified: json['is_verified'] ?? false,
      contactPhone: json['contact_phone'],
    );
  }
}
