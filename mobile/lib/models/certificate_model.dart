class CertificateModel {
  final String certificateId;
  final int donationId;
  final String donorName;
  final String organizationType;
  final String foodName;
  final double quantity;
  final String quantityUnit;
  final String receivingNgo;
  final String completedAt;
  final String verificationHash;
  final double co2SavedKg;
  final double waterSavedLiters;
  final String title;
  final String disclaimer;

  CertificateModel({
    required this.certificateId,
    required this.donationId,
    required this.donorName,
    required this.organizationType,
    required this.foodName,
    required this.quantity,
    required this.quantityUnit,
    required this.receivingNgo,
    required this.completedAt,
    required this.verificationHash,
    required this.co2SavedKg,
    required this.waterSavedLiters,
    this.title = 'Certificate of Participation in Food Donation',
    this.disclaimer = 'Issued for voluntary surplus food redistribution and community hunger relief.',
  });

  factory CertificateModel.fromJson(Map<String, dynamic> json) {
    return CertificateModel(
      certificateId: json['certificate_id'] ?? '',
      donationId: json['donation_id'] ?? 0,
      donorName: json['donor_name'] ?? 'Verified Donor',
      organizationType: json['organization_type'] ?? 'Food Business Partner',
      foodName: json['food_name'] ?? '',
      quantity: (json['quantity'] as num).toDouble(),
      quantityUnit: json['quantity_unit'] ?? 'Meals',
      receivingNgo: json['receiving_ngo'] ?? 'Community Partner NGO',
      completedAt: json['completed_at'] ?? '',
      verificationHash: json['verification_hash'] ?? '',
      co2SavedKg: (json['co2_saved_kg'] as num).toDouble(),
      waterSavedLiters: (json['water_saved_liters'] as num).toDouble(),
      title: json['title'] ?? 'Certificate of Participation in Food Donation',
      disclaimer: json['disclaimer'] ?? 'Issued for voluntary surplus food redistribution and community hunger relief.',
    );
  }
}

class CSRImpactSummaryModel {
  final int donorId;
  final String donorName;
  final int totalDonations;
  final double totalMealsDonated;
  final double totalCo2AvoidedKg;
  final double totalWaterConservedLiters;
  final double estimatedDisposalCostAvoidedInr;
  final int verifiedNgoPartnersCount;
  final double trustScore;
  final bool isVerifiedDonor;

  CSRImpactSummaryModel({
    required this.donorId,
    required this.donorName,
    required this.totalDonations,
    required this.totalMealsDonated,
    required this.totalCo2AvoidedKg,
    required this.totalWaterConservedLiters,
    required this.estimatedDisposalCostAvoidedInr,
    required this.verifiedNgoPartnersCount,
    required this.trustScore,
    required this.isVerifiedDonor,
  });

  factory CSRImpactSummaryModel.fromJson(Map<String, dynamic> json) {
    return CSRImpactSummaryModel(
      donorId: json['donor_id'] ?? 0,
      donorName: json['donor_name'] ?? '',
      totalDonations: json['total_donations'] ?? 0,
      totalMealsDonated: (json['total_meals_donated'] as num).toDouble(),
      totalCo2AvoidedKg: (json['total_co2_avoided_kg'] as num).toDouble(),
      totalWaterConservedLiters: (json['total_water_conserved_liters'] as num).toDouble(),
      estimatedDisposalCostAvoidedInr: (json['estimated_disposal_cost_avoided_inr'] as num).toDouble(),
      verifiedNgoPartnersCount: json['verified_ngo_partners_count'] ?? 0,
      trustScore: (json['trust_score'] as num).toDouble(),
      isVerifiedDonor: json['is_verified_donor'] ?? true,
    );
  }
}
