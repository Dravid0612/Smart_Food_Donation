import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/primary_action_button.dart';
import '../../widgets/skeleton_loader.dart';

/// Comprehensive Donor Impact & Motivation Dashboard
class DonorImpactDashboardScreen extends StatefulWidget {
  const DonorImpactDashboardScreen({super.key});

  @override
  State<DonorImpactDashboardScreen> createState() => _DonorImpactDashboardScreenState();
}

class _DonorImpactDashboardScreenState extends State<DonorImpactDashboardScreen> {
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    final prov = Provider.of<DonationProvider>(context, listen: false);
    _isLoading = prov.donorImpact == null;
    _loadImpact();
  }

  Future<void> _loadImpact() async {
    final prov = Provider.of<DonationProvider>(context, listen: false);
    if (prov.donorImpact == null) {
      setState(() => _isLoading = true);
      await prov.fetchDonorImpactSummary();
    } else {
      _isLoading = false;
    }
    if (mounted) setState(() => _isLoading = false);
  }

  void _showCalculationExplanation(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusFeatureCard)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(AppTheme.space24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(context.tr('impact_dashboard'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context)),
                ],
              ),
              const Divider(height: 20),
              _buildCalculationRow(
                context.tr('meals_rescued'),
                context.tr('impact_summary'),
              ),
              _buildCalculationRow(
                context.tr('co2_saved'),
                '0.45 kg / meal',
              ),
              const SizedBox(height: AppTheme.space16),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCalculationRow(String label, String formula) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppTheme.space12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.primaryGreen)),
          const SizedBox(height: 2),
          Text(formula, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final impact = prov.donorImpact;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('impact_dashboard')),
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            tooltip: context.tr('impact_dashboard'),
            onPressed: () => _showCalculationExplanation(context),
          ),
        ],
      ),
      body: _isLoading
          ? const Padding(
              padding: EdgeInsets.all(AppTheme.space16),
              child: SkeletonLoader(width: double.infinity, height: 400),
            )
          : RefreshIndicator(
              onRefresh: _loadImpact,
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(AppTheme.space16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Platform Recognition Banner
                    _buildRecognitionCard(impact?.recognitionLevel ?? context.tr('verified_partner').toUpperCase()),
                    const SizedBox(height: AppTheme.space16),

                    // Primary Separated Metrics Grid (5 Authoritative Environmental/Social Indicators)
                    Text(
                      context.tr('impact_summary').toUpperCase(),
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary, letterSpacing: 0.5),
                    ),
                    const SizedBox(height: AppTheme.space8),
                    Row(
                      children: [
                        Expanded(
                          child: _buildMetricCard(
                            title: context.tr('meals_rescued'),
                            value: '${impact?.mealsRescued.toInt() ?? 0}',
                            subtitle: 'Rescued meals delivered',
                            color: AppTheme.primaryGreen,
                            icon: Icons.restaurant_rounded,
                          ),
                        ),
                        const SizedBox(width: AppTheme.space8),
                        Expanded(
                          child: _buildMetricCard(
                            title: 'Food Recovered',
                            value: '${(impact?.estimatedWasteDivertedKg ?? ((impact?.mealsRescued ?? 0) * 0.45)).toStringAsFixed(1)} kg',
                            subtitle: 'Edible food saved',
                            color: AppTheme.info,
                            icon: Icons.scale_rounded,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppTheme.space8),
                    Row(
                      children: [
                        Expanded(
                          child: _buildMetricCard(
                            title: 'Estimated CO2e',
                            value: '${((impact?.mealsRescued ?? 0) * 0.45).toStringAsFixed(1)} kg',
                            subtitle: 'Estimated greenhouse gases prevented',
                            color: AppTheme.warning,
                            icon: Icons.eco_rounded,
                          ),
                        ),
                        const SizedBox(width: AppTheme.space8),
                        Expanded(
                          child: _buildMetricCard(
                            title: 'Estimated Water',
                            value: '${((impact?.mealsRescued ?? 0) * 180).toInt()} L',
                            subtitle: 'Embedded water footprint conserved',
                            color: const Color(0xFF0284C7),
                            icon: Icons.water_drop_rounded,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppTheme.space8),
                    _buildMetricCard(
                      title: 'Estimated Disposal Cost Avoided',
                      value: '₹${((impact?.mealsRescued ?? 0) * 12).toInt()}',
                      subtitle: 'Estimated municipal waste processing cost saved',
                      color: AppTheme.secondaryTerracotta,
                      icon: Icons.savings_outlined,
                    ),
                    const SizedBox(height: AppTheme.space16),

                    // Mandatory Non-Binding Estimate / No Tax Write-off Disclaimer
                    Container(
                      padding: const EdgeInsets.all(AppTheme.space12),
                      decoration: BoxDecoration(
                        color: Colors.amber.shade50,
                        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                        border: Border.all(color: Colors.amber.shade200),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.info_outline_rounded, color: Colors.amber.shade800, size: 18),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              context.tr('tax_deduction_disclaimer'),
                              style: TextStyle(
                                fontSize: 11.5,
                                color: Colors.amber.shade900,
                                height: 1.35,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppTheme.space20),

                    // Primary CTA: Donate Again
                    PrimaryActionButton(
                      label: context.tr('donate_now').toUpperCase(),
                      icon: Icons.add_circle_outline,
                      onPressed: () => context.push('/donor/create'),
                    ),
                    const SizedBox(height: AppTheme.space12),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: () => context.push('/donor/history'),
                        icon: const Icon(Icons.receipt_long),
                        label: Text(context.tr('certificate').toUpperCase()),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: AppTheme.space14),
                          side: const BorderSide(color: AppTheme.border),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                        ),
                      ),
                    ),
                    const SizedBox(height: AppTheme.space20),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildRecognitionCard(String level) {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.primaryDark, AppTheme.primaryGreen],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.workspace_premium, color: Colors.amber, size: 28),
          ),
          const SizedBox(width: AppTheme.space16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.tr('verified_partner').toUpperCase(),
                  style: const TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                ),
                const SizedBox(height: 2),
                Text(
                  level,
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required String subtitle,
    required Color color,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Icon(icon, color: color, size: 18),
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space12),
          Text(
            value,
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: color, letterSpacing: -0.5),
          ),
          const SizedBox(height: 2),
          Text(
            title,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
          ),
          Text(
            subtitle,
            style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
          ),
        ],
      ),
    );
  }
}
