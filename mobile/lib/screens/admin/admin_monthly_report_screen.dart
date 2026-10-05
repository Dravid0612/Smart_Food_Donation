import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../models/admin_operations_model.dart';
import '../../providers/admin_provider.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';

class AdminMonthlyReportScreen extends StatefulWidget {
  final AdminMonthlyReportModel? initialReport;
  final AdminRepeatDonorInsightsModel? initialInsights;

  const AdminMonthlyReportScreen({
    super.key,
    this.initialReport,
    this.initialInsights,
  });

  @override
  State<AdminMonthlyReportScreen> createState() => _AdminMonthlyReportScreenState();
}

class _AdminMonthlyReportScreenState extends State<AdminMonthlyReportScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    if (widget.initialReport == null && widget.initialInsights == null) {
      _isLoading = true;
      WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    final adminProv = Provider.of<AdminProvider>(context, listen: false);
    await Future.wait([
      adminProv.fetchMonthlyImpactReport(),
      adminProv.fetchRepeatDonorWasteInsights(),
    ]);
    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);
    final report = widget.initialReport ?? adminProv.monthlyReport;
    final insights = widget.initialInsights ?? adminProv.wasteInsights;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(
          context.tr('monthly_impact_report'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        bottom: TabBar(
          controller: _tabController,
          labelColor: AppTheme.primaryDark,
          unselectedLabelColor: AppTheme.textSecondary,
          indicatorColor: AppTheme.primaryGreen,
          tabs: [
            Tab(text: context.tr('monthly_impact_report')),
            Tab(text: context.tr('waste_prevention_insights')),
            Tab(text: context.tr('fssai_info_title')),
          ],
        ),
      ),
      body: _isLoading
          ? const LoadingStateWidget(message: 'Generating operational report...')
          : TabBarView(
              controller: _tabController,
              children: [
                // ── TAB 1: MONTHLY IMPACT REPORT ──
                _buildMonthlyImpactTab(report),

                // ── TAB 2: WASTE-PREVENTION INSIGHTS ──
                _buildWasteInsightsTab(insights),

                // ── TAB 3: FSSAI INFORMATION ──
                _buildFssaiTab(),
              ],
            ),
    );
  }

  Widget _buildMonthlyImpactTab(AdminMonthlyReportModel? report) {
    if (report == null) {
      return const EmptyStateWidget(
        icon: Icons.analytics_outlined,
        title: 'No Monthly Report',
        description: 'No verified monthly impact data is currently available.',
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppTheme.space16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Month Header
          Container(
            padding: const EdgeInsets.all(AppTheme.space14),
            decoration: BoxDecoration(
              color: AppTheme.card,
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Reporting Month', style: TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                    Text(
                      report.month,
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryGreen.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                  ),
                  child: Text(
                    '${report.completedRescues} Rescues Completed',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryDark),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppTheme.space16),

          // Operational Rescue Metrics Card
          const Text('Verified Operational Quantities', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
          const SizedBox(height: AppTheme.space8),
          Container(
            padding: const EdgeInsets.all(AppTheme.space14),
            decoration: BoxDecoration(
              color: AppTheme.card,
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildReportMetric('Meals Rescued', '${report.mealsRescued.toInt()}', color: AppTheme.primaryDark),
                    _buildReportMetric('Food Recovered', '${report.foodRecoveredKg.toStringAsFixed(1)} kg', color: AppTheme.primaryGreen),
                    _buildReportMetric('Rescues Completed', '${report.completedRescues}', color: const Color(0xFF0284C7)),
                  ],
                ),
                const Divider(height: AppTheme.space20, color: AppTheme.divider),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildReportMetric('Intake Received', '${report.receivedQuantity.toInt()} meals'),
                    _buildReportMetric('Distributed to Need', '${report.distributedQuantity.toInt()} meals'),
                    _buildReportMetric('Avg Time', '${report.avgRescueCompletionMinutes.toStringAsFixed(1)} min'),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: AppTheme.space16),

          // Estimated Environmental & Cost Metrics Card (Section 17)
          Row(
            children: [
              const Text('Environmental & Cost Avoided', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.warning.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  context.tr('estimated_label').toUpperCase(),
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFFC05621)),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space8),
          Container(
            padding: const EdgeInsets.all(AppTheme.space14),
            decoration: BoxDecoration(
              color: AppTheme.card,
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildReportMetric(
                      'CO2e Averted (${context.tr('estimated_label')})',
                      '${report.estimatedCo2eKg.toStringAsFixed(1)} kg',
                      color: AppTheme.primaryGreen,
                    ),
                    _buildReportMetric(
                      'Water Saved (${context.tr('estimated_label')})',
                      '${report.estimatedWaterLiters.toInt()} L',
                      color: const Color(0xFF0284C7),
                    ),
                  ],
                ),
                const Divider(height: AppTheme.space20, color: AppTheme.divider),
                Row(
                  children: [
                    _buildReportMetric(
                      'Disposal Cost Avoided (${context.tr('estimated_label')})',
                      '₹${report.estimatedDisposalCostAvoidedInr.toStringAsFixed(0)}',
                      color: const Color(0xFFD97706),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: AppTheme.space16),

          // Prominent Integrity Disclaimer
          Container(
            padding: const EdgeInsets.all(AppTheme.space12),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.info_outline, size: 18, color: AppTheme.textSecondary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    context.tr('impact_disclaimer'),
                    style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWasteInsightsTab(AdminRepeatDonorInsightsModel? insights) {
    if (insights == null || insights.patterns.isEmpty) {
      return const EmptyStateWidget(
        icon: Icons.trending_up,
        title: 'No Surplus Patterns Yet',
        description: 'Repeat donor history will automatically identify weekly surplus timing patterns.',
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppTheme.space16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(AppTheme.space12),
            decoration: BoxDecoration(
              color: AppTheme.primaryGreen.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.2)),
            ),
            child: Row(
              children: [
                const Icon(Icons.eco_outlined, color: AppTheme.primaryDark, size: 22),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Analyzed ${insights.totalDonationsAnalyzed} verified donations to detect weekly surplus timing. Helps coordinators avert surplus waste at the source.',
                    style: const TextStyle(fontSize: 12, color: AppTheme.primaryDark),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppTheme.space16),

          const Text('Weekly Recurring Surplus Patterns', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
          const SizedBox(height: AppTheme.space8),

          ...insights.patterns.map((p) {
            return Container(
              margin: const EdgeInsets.only(bottom: AppTheme.space10),
              padding: const EdgeInsets.all(AppTheme.space14),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                border: Border.all(color: AppTheme.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        '${p.dayOfWeek} • ${p.foodCategory}',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.surface,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppTheme.border),
                        ),
                        child: Text(
                          '${p.donationCount} rescues',
                          style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Avg Surplus: ${p.avgSurplus.toStringAsFixed(0)} meals', style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
                      Text('Rescued: ${p.avgRescued.toStringAsFixed(0)} meals', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen)),
                    ],
                  ),
                  if (p.topDonors.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      'Recurring partners: ${p.topDonors.join(", ")}',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textMuted, fontStyle: FontStyle.italic),
                    ),
                  ],
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildFssaiTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppTheme.space16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(AppTheme.space14),
            decoration: BoxDecoration(
              color: AppTheme.card,
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.health_and_safety_outlined, color: AppTheme.primaryDark, size: 24),
                    const SizedBox(width: 8),
                    Text(
                      context.tr('fssai_info_title'),
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.warning.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    context.tr('fssai_info_disclaimer'),
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFFC05621)),
                  ),
                ),
                const Divider(height: AppTheme.space24, color: AppTheme.divider),
                _buildGuidanceItem(
                  'Temperature Control Guidelines',
                  'Cooked surplus foods must be maintained hot (above 65°C) or promptly chilled (below 5°C). Avoid keeping food in the danger zone (5°C - 65°C) for more than 2 hours.',
                ),
                const SizedBox(height: 12),
                _buildGuidanceItem(
                  'Hygienic Transit & Packaging',
                  'All food containers must be sealed or securely covered with food-grade covers to protect against environmental contamination during volunteer or NGO transit.',
                ),
                const SizedBox(height: 12),
                _buildGuidanceItem(
                  'Immediate Intake Inspection',
                  'NGO receiving personnel must verify odor, texture, and visual condition upon arrival before accepting intake.',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGuidanceItem(String title, String desc) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
        const SizedBox(height: 3),
        Text(desc, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, height: 1.35)),
      ],
    );
  }

  Widget _buildReportMetric(String label, String value, {Color? color}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: color ?? AppTheme.textPrimary),
        ),
      ],
    );
  }
}
