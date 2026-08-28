class RecurringDonationModel {
  final int id;
  final int donorId;
  final String templateName;
  final String foodName;
  final String foodCategory;
  final double typicalQuantity;
  final String quantityUnit;
  final String frequency;
  final String preferredPickupTime;
  final String pickupAddress;
  final String? storageMethod;
  final String? packagingCondition;
  final bool isActive;
  final String createdAt;

  RecurringDonationModel({
    required this.id,
    required this.donorId,
    required this.templateName,
    required this.foodName,
    required this.foodCategory,
    required this.typicalQuantity,
    required this.quantityUnit,
    required this.frequency,
    required this.preferredPickupTime,
    required this.pickupAddress,
    this.storageMethod,
    this.packagingCondition,
    required this.isActive,
    required this.createdAt,
  });

  factory RecurringDonationModel.fromJson(Map<String, dynamic> json) {
    return RecurringDonationModel(
      id: json['id'],
      donorId: json['donor_id'],
      templateName: json['template_name'] ?? '',
      foodName: json['food_name'] ?? '',
      foodCategory: json['food_category'] ?? 'Cooked Food',
      typicalQuantity: (json['typical_quantity'] as num).toDouble(),
      quantityUnit: json['quantity_unit'] ?? 'Meals',
      frequency: json['frequency'] ?? 'Daily',
      preferredPickupTime: json['preferred_pickup_time'] ?? '20:30',
      pickupAddress: json['pickup_address'] ?? '',
      storageMethod: json['storage_method'],
      packagingCondition: json['packaging_condition'],
      isActive: json['is_active'] ?? true,
      createdAt: json['created_at'] ?? '',
    );
  }
}
