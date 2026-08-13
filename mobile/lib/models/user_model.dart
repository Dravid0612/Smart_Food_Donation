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
  });

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
    };
  }
}
