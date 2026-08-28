/// Authentic Model representing Donor Impact Summary and Monthly Aggregations
class DonorMonthlyImpactModel {
  final String month;
  final int donationsCount;
  final double mealsDonated;
  final double mealsRescued;
  final double mealsDistributed;
  final double wasteDivertedKg;
  final int successfulRescues;
  final int partnerNgosCount;

  const DonorMonthlyImpactModel({
    required this.month,
    required this.donationsCount,
    required this.mealsDonated,
    required this.mealsRescued,
    required this.mealsDistributed,
    required this.wasteDivertedKg,
    required this.successfulRescues,
    required this.partnerNgosCount,
  });

  factory DonorMonthlyImpactModel.fromJson(Map<String, dynamic> json) {
    return DonorMonthlyImpactModel(
      month: json['month'] ?? 'Current Month',
      donationsCount: json['donations_count'] ?? 0,
      mealsDonated: (json['meals_donated'] as num?)?.toDouble() ?? 0.0,
      mealsRescued: (json['meals_rescued'] as num?)?.toDouble() ?? 0.0,
      mealsDistributed: (json['meals_distributed'] as num?)?.toDouble() ?? 0.0,
      wasteDivertedKg: (json['waste_diverted_kg'] as num?)?.toDouble() ?? 0.0,
      successfulRescues: json['successful_rescues'] ?? 0,
      partnerNgosCount: json['partner_ngos_count'] ?? 0,
    );
  }
}

class DonorImpactSummaryModel {
  final int donorId;
  final String donorName;
  final int totalDonationsCount;
  final int successfulRescuesCount;
  final double mealsDonated;
  final double mealsRescued;
  final double mealsDistributed;
  final double estimatedWasteDivertedKg;
  final double estimatedValuePreservedInr;
  final int partnerNgosCount;
  final String recognitionLevel;
  final double completionRatePercent;
  final String conversionFactorNote;
  final List<DonorMonthlyImpactModel> monthlyBreakdown;

  const DonorImpactSummaryModel({
    required this.donorId,
    required this.donorName,
    required this.totalDonationsCount,
    required this.successfulRescuesCount,
    required this.mealsDonated,
    required this.mealsRescued,
    required this.mealsDistributed,
    required this.estimatedWasteDivertedKg,
    required this.estimatedValuePreservedInr,
    required this.partnerNgosCount,
    required this.recognitionLevel,
    required this.completionRatePercent,
    required this.conversionFactorNote,
    required this.monthlyBreakdown,
  });

  factory DonorImpactSummaryModel.fromJson(Map<String, dynamic> json) {
    final breakdownList = (json['monthly_breakdown'] as List<dynamic>?)
            ?.map((e) => DonorMonthlyImpactModel.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];

    return DonorImpactSummaryModel(
      donorId: json['donor_id'] ?? 0,
      donorName: json['donor_name'] ?? 'Donor',
      totalDonationsCount: json['total_donations_count'] ?? 0,
      successfulRescuesCount: json['successful_rescues_count'] ?? 0,
      mealsDonated: (json['meals_donated'] as num?)?.toDouble() ?? 0.0,
      mealsRescued: (json['meals_rescued'] as num?)?.toDouble() ?? 0.0,
      mealsDistributed: (json['meals_distributed'] as num?)?.toDouble() ?? 0.0,
      estimatedWasteDivertedKg: (json['estimated_waste_diverted_kg'] as num?)?.toDouble() ?? 0.0,
      estimatedValuePreservedInr: (json['estimated_value_preserved_inr'] as num?)?.toDouble() ?? 0.0,
      partnerNgosCount: json['partner_ngos_count'] ?? 0,
      recognitionLevel: json['recognition_level'] ?? 'NEW SUPPORTER',
      completionRatePercent: (json['completion_rate_percent'] as num?)?.toDouble() ?? 0.0,
      conversionFactorNote: json['conversion_factor_note'] ??
          'Estimated waste diverted = completed rescued meals × 0.45 kg project estimation factor.',
      monthlyBreakdown: breakdownList,
    );
  }
}
