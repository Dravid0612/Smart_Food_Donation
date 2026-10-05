import 'dart:convert';

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
  final Map<String, dynamic>? operatingHours;
  final Map<String, dynamic>? demandRequirements;

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
    this.operatingHours,
    this.demandRequirements,
  });

  factory NgoModel.fromJson(Map<String, dynamic> json) {
    Map<String, dynamic>? parsedHours;
    if (json['operating_hours'] is Map<String, dynamic>) {
      parsedHours = json['operating_hours'] as Map<String, dynamic>;
    } else if (json['operating_hours'] is String && (json['operating_hours'] as String).isNotEmpty) {
      try {
        final decoded = jsonDecode(json['operating_hours'] as String);
        if (decoded is Map<String, dynamic>) {
          parsedHours = decoded;
        }
      } catch (_) {}
    }

    Map<String, dynamic>? parsedDemands;
    if (json['demand_requirements'] is Map<String, dynamic>) {
      parsedDemands = json['demand_requirements'] as Map<String, dynamic>;
    } else if (json['demand_requirements'] is String && (json['demand_requirements'] as String).isNotEmpty) {
      try {
        final decoded = jsonDecode(json['demand_requirements'] as String);
        if (decoded is Map<String, dynamic>) {
          parsedDemands = decoded;
        }
      } catch (_) {}
    }

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
      operatingHours: parsedHours,
      demandRequirements: parsedDemands,
    );
  }

  NgoModel copyWith({
    int? id,
    int? userId,
    String? organizationName,
    String? description,
    String? address,
    double? latitude,
    double? longitude,
    int? capacity,
    int? currentCapacity,
    bool? isAvailable,
    bool? isVerified,
    String? contactPhone,
    Map<String, dynamic>? operatingHours,
    Map<String, dynamic>? demandRequirements,
  }) {
    return NgoModel(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      organizationName: organizationName ?? this.organizationName,
      description: description ?? this.description,
      address: address ?? this.address,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      capacity: capacity ?? this.capacity,
      currentCapacity: currentCapacity ?? this.currentCapacity,
      isAvailable: isAvailable ?? this.isAvailable,
      isVerified: isVerified ?? this.isVerified,
      contactPhone: contactPhone ?? this.contactPhone,
      operatingHours: operatingHours ?? this.operatingHours,
      demandRequirements: demandRequirements ?? this.demandRequirements,
    );
  }
}

