class DonationHistoryModel {
  final int id;
  final int donationId;
  final String? oldStatus;
  final String newStatus;
  final int? changedBy;
  final String? remarks;
  final String createdAt;

  DonationHistoryModel({
    required this.id,
    required this.donationId,
    this.oldStatus,
    required this.newStatus,
    this.changedBy,
    this.remarks,
    required this.createdAt,
  });

  factory DonationHistoryModel.fromJson(Map<String, dynamic> json) {
    return DonationHistoryModel(
      id: json['id'],
      donationId: json['donation_id'],
      oldStatus: json['old_status'],
      newStatus: json['new_status'] ?? '',
      changedBy: json['changed_by'],
      remarks: json['remarks'],
      createdAt: json['created_at'] ?? '',
    );
  }
}

class DonationModel {
  final int id;
  final int donorId;
  final String foodName;
  final String? description;
  final String foodCategory;
  final double quantity;
  final String quantityUnit;
  final String preparationTime;
  final String expiryTime;
  final String pickupAddress;
  final double? latitude;
  final double? longitude;
  final String? imageUrl;
  final String status;
  final int? assignedNgoId;
  final int? assignedVolunteerId;
  final String createdAt;
  final String urgencyLevel;
  final String? donorName;
  final String? donorPhone;
  final String? ngoName;
  final String? volunteerName;
  final String? volunteerPhone;
  final List<DonationHistoryModel> history;

  DonationModel({
    required this.id,
    required this.donorId,
    required this.foodName,
    this.description,
    required this.foodCategory,
    required this.quantity,
    required this.quantityUnit,
    required this.preparationTime,
    required this.expiryTime,
    required this.pickupAddress,
    this.latitude,
    this.longitude,
    this.imageUrl,
    required this.status,
    this.assignedNgoId,
    this.assignedVolunteerId,
    required this.createdAt,
    this.urgencyLevel = 'Fresh',
    this.donorName,
    this.donorPhone,
    this.ngoName,
    this.volunteerName,
    this.volunteerPhone,
    this.history = const [],
  });

  factory DonationModel.fromJson(Map<String, dynamic> json) {
    var historyList = <DonationHistoryModel>[];
    if (json['history'] != null) {
      historyList = (json['history'] as List)
          .map((h) => DonationHistoryModel.fromJson(h))
          .toList();
    }

    return DonationModel(
      id: json['id'],
      donorId: json['donor_id'],
      foodName: json['food_name'] ?? '',
      description: json['description'],
      foodCategory: json['food_category'] ?? 'Other',
      quantity: (json['quantity'] as num).toDouble(),
      quantityUnit: json['quantity_unit'] ?? 'Meals',
      preparationTime: json['preparation_time'] ?? '',
      expiryTime: json['expiry_time'] ?? '',
      pickupAddress: json['pickup_address'] ?? '',
      latitude: json['latitude'] != null ? (json['latitude'] as num).toDouble() : null,
      longitude: json['longitude'] != null ? (json['longitude'] as num).toDouble() : null,
      imageUrl: json['image_url'],
      status: json['status'] ?? 'pending',
      assignedNgoId: json['assigned_ngo_id'],
      assignedVolunteerId: json['assigned_volunteer_id'],
      createdAt: json['created_at'] ?? '',
      urgencyLevel: json['urgency_level'] ?? 'Fresh',
      donorName: json['donor_name'],
      donorPhone: json['donor_phone'],
      ngoName: json['ngo_name'],
      volunteerName: json['volunteer_name'],
      volunteerPhone: json['volunteer_phone'],
      history: historyList,
    );
  }
}
