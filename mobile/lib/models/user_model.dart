class UserModel {
  final int id;
  final String name;
  final String email;
  final String? phone;
  final String role; // donor, ngo, volunteer, admin
  final String? address;
  final double? latitude;
  final double? longitude;
  final String? profileImage;
  final bool isActive;
  final double donorTrustScore;
  final int totalMealsDonated;
  final double reliabilityScore;
  final String vehicleType;
  final int carryingCapacity;
  final bool phoneVerified;
  final String? phoneCountryCode;
  final String? phoneNormalized;

  UserModel({
    required this.id,
    required this.name,
    required this.email,
    this.phone,
    required this.role,
    this.address,
    this.latitude,
    this.longitude,
    this.profileImage,
    required this.isActive,
    this.donorTrustScore = 5.0,
    this.totalMealsDonated = 0,
    this.reliabilityScore = 100.0,
    this.vehicleType = 'Bike',
    this.carryingCapacity = 25,
    this.phoneVerified = false,
    this.phoneCountryCode = '+91',
    this.phoneNormalized,
  });

  String? get phoneMasked {
    final p = phoneNormalized ?? phone;
    if (p == null || p.isEmpty) return null;
    final digits = p.replaceAll(RegExp(r'\D'), '');
    if (digits.length >= 4) {
      final last4 = digits.substring(digits.length - 4);
      if (p.startsWith('+')) {
        final prefix = p.length > 3 ? p.substring(0, 3) : p.substring(0, 2);
        return '$prefix ****$last4';
      }
      return '****$last4';
    }
    return '****';
  }

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'],
      name: json['name'] ?? '',
      email: json['email'] ?? '',
      phone: json['phone'],
      role: json['role'] ?? 'donor',
      address: json['address'],
      latitude: json['latitude'] != null ? (json['latitude'] as num).toDouble() : null,
      longitude: json['longitude'] != null ? (json['longitude'] as num).toDouble() : null,
      profileImage: json['profile_image'],
      isActive: json['is_active'] ?? true,
      phoneVerified: json['phone_verified'] ?? false,
      phoneCountryCode: json['phone_country_code'] ?? '+91',
      phoneNormalized: json['phone_normalized'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'phone': phone,
      'role': role,
      'address': address,
      'latitude': latitude,
      'longitude': longitude,
      'profile_image': profileImage,
      'is_active': isActive,
      'phone_verified': phoneVerified,
      'phone_country_code': phoneCountryCode,
      'phone_normalized': phoneNormalized,
    };
  }
}

