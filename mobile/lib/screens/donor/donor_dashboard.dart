import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/donation_provider.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/donation_card.dart';
import '../../widgets/trust_badge.dart';
import '../../widgets/skeleton_loader.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/error_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';

/// Production-Grade Donor Dashboard with Motivation, Trust, and Real Impact Tracking
class DonorDashboardScreen extends StatefulWidget {
  const DonorDashboardScreen({super.key});

  @override
  State<DonorDashboardScreen> createState() => _DonorDashboardScreenState();
}

class _DonorDashboardScreenState extends State<DonorDashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadData();
    });
  }

  Future<void> _loadData() async {
    final donationProv = Provider.of<DonationProvider>(context, listen: false);
    final notifProv = Provider.of<NotificationProvider>(context, listen: false);
    await Future.wait([
      donationProv.fetchDonations(myDonationsOnly: true),
      donationProv.fetchDonorImpactSummary(),
      notifProv.fetchNotifications(),
    ]);
  }

  String _getGreeting(BuildContext context) {
    final hour = DateTime.now().hour;
    if (hour < 12) return context.tr('good_morning');
    if (hour < 17) return context.tr('good_afternoon');
    return context.tr('good_evening');
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final donationProv = Provider.of<DonationProvider>(context);
    final notifProv = Provider.of<NotificationProvider>(context);

    final user = auth.currentUser;
    final donations = donationProv.donations;
    final impact = donationProv.donorImpact;

    final completedList = donations.where((d) => ['completed', 'delivered'].contains(d.status.toLowerCase())).toList();
    final totalMealsRescued = impact?.mealsRescued ?? completedList.fold<double>(0.0, (sum, d) => sum + d.quantity);
    final wasteKgPrevented = (impact?.estimatedWasteDivertedKg ?? (totalMealsRescued * 0.45)).toStringAsFixed(1);
    final activeDonations = donations.where((d) => !['completed', 'delivered', 'cancelled', 'expired'].contains(d.status.toLowerCase())).toList();

    final isFirstTimeDonor = donations.isEmpty;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${_getGreeting(context)}, ${user?.name ?? context.tr('role_donor')}',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, letterSpacing: -0.2),
            ),
            Row(
              children: [
                TrustBadge(label: context.tr('verified_partner'), isVerified: true),
                const SizedBox(width: AppTheme.space8),
                Text(
                  user?.address ?? context.tr('role_donor'),
                  style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ],
        ),
        actions: [
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.notifications_outlined),
                onPressed: () => context.push('/notifications'),
              ),
              if (notifProv.unreadCount > 0)
                Positioned(
                  right: 8,
                  top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: AppTheme.error,
                      shape: BoxShape.circle,
                    ),
                    child: Text(
                      '${notifProv.unreadCount}',
                      style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppTheme.space16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Quick Info Action Chips (Why Donate / How It Works / Impact) ──
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildNavChip(
                      icon: Icons.help_outline,
                      label: context.tr('why_donate'),
                      color: AppTheme.primaryGreen,
                      onTap: () => context.push('/donor/why-donate'),
                    ),
                    const SizedBox(width: 8),
                    _buildNavChip(
                      icon: Icons.alt_route_outlined,
                      label: context.tr('how_it_works'),
                      color: AppTheme.info,
                      onTap: () => context.push('/donor/how-it-works'),
                    ),
                    const SizedBox(width: 8),
                    _buildNavChip(
                      icon: Icons.insights_outlined,
                      label: context.tr('impact_dashboard'),
                      color: AppTheme.secondaryTerracotta,
                      onTap: () => context.push('/donor/impact'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),

              // ── 1. PRIMARY HERO BANNER ─────────────────────────────────────
              if (isFirstTimeDonor)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppTheme.space20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [AppTheme.primaryGreen, AppTheme.primaryDark],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                    boxShadow: AppTheme.shadowFeature,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                        ),
                        child: Text(
                          context.tr('donate_now').toUpperCase(),
                          style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                        ),
                      ),
                      const SizedBox(height: AppTheme.space12),
                      Text(
                        context.tr('tagline'),
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold, height: 1.3),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        context.tr('donate_surplus_desc'),
                        style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.4),
                      ),
                      const SizedBox(height: AppTheme.space16),
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: () => context.push('/donor/create'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.white,
                                foregroundColor: AppTheme.primaryDark,
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                              ),
                              icon: const Icon(Icons.add_circle, size: 20),
                              label: Text(context.tr('donate_now').toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold)),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                )
              else
                // Repeat Donor Hero Impact Summary Card
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppTheme.space16),
                  decoration: BoxDecoration(
                    color: AppTheme.card,
                    borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                    border: Border.all(color: AppTheme.border),
                    boxShadow: AppTheme.shadowCard,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.workspace_premium, color: Colors.amber, size: 20),
                              const SizedBox(width: 6),
                              Text(
                                impact?.recognitionLevel ?? context.tr('verified_partner').toUpperCase(),
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                              ),
                            ],
                          ),
                          TextButton(
                            onPressed: () => context.push('/donor/impact'),
                            child: Text('${context.tr('impact_dashboard')} →', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                          ),
                        ],
                      ),
                      const Divider(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _buildImpactMetric('${totalMealsRescued.toInt()}', context.tr('meals_rescued'), Icons.check_circle_outline, AppTheme.primaryGreen),
                          Container(height: 36, width: 1, color: AppTheme.border),
                          _buildImpactMetric('$wasteKgPrevented kg', context.tr('co2_saved'), Icons.eco, AppTheme.success),
                          Container(height: 36, width: 1, color: AppTheme.border),
                          _buildImpactMetric('${impact?.successfulRescuesCount ?? completedList.length}', context.tr('completed_donations'), Icons.task_alt, AppTheme.secondaryTerracotta),
                        ],
                      ),
                      const SizedBox(height: AppTheme.space16),
                      SizedBox(
                        width: double.infinity,
                        height: 48,
                        child: ElevatedButton.icon(
                          onPressed: () => context.push('/donor/create'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryGreen,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                          ),
                          icon: const Icon(Icons.add_circle, size: 20),
                          label: Text('+ ${context.tr('donate_now')}', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                ),

              const SizedBox(height: AppTheme.space20),

              // ── 1.5. PROACTIVE TIME-CRITICAL RESCUE ALERT BANNER ──────────────
              ...(() {
                final urgentCriticalDonations = activeDonations.where((d) {
                  final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
                  return urg == 'URGENT' || urg == 'CRITICAL';
                }).toList();

                if (urgentCriticalDonations.isEmpty) return <Widget>[];

                final isCritical = urgentCriticalDonations.any((d) =>
                    (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase() == 'CRITICAL');

                return <Widget>[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(AppTheme.space14),
                    margin: const EdgeInsets.only(bottom: AppTheme.space16),
                    decoration: BoxDecoration(
                      color: isCritical ? const Color(0xFFFEF2F2) : const Color(0xFFFFFBEB),
                      borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                      border: Border.all(
                        color: isCritical ? const Color(0xFFFECACA) : const Color(0xFFFDE68A),
                        width: 1.2,
                      ),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: (isCritical ? AppTheme.error : AppTheme.secondaryTerracotta)
                                .withValues(alpha: 0.12),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            Icons.radar,
                            color: isCritical ? AppTheme.error : AppTheme.secondaryTerracotta,
                            size: 22,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Text(
                                    context.tr('proactive_outreach_active'),
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                      color: isCritical ? const Color(0xFF991B1B) : const Color(0xFF92400E),
                                    ),
                                  ),
                                  const Spacer(),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: isCritical ? AppTheme.error : AppTheme.secondaryTerracotta,
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Text(
                                      '${urgentCriticalDonations.length} ${isCritical ? "CRITICAL" : "URGENT"}',
                                      style: const TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.white,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                isCritical
                                    ? context.tr('proactive_reassurance_critical')
                                    : context.tr('proactive_reassurance_urgent'),
                                style: TextStyle(
                                  fontSize: 12.5,
                                  color: isCritical ? const Color(0xFF7F1D1D) : const Color(0xFF78350F),
                                  height: 1.3,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ];
              })(),

              // ── 2. ACTIVE RESCUES TRACKER ─────────────────────────────────
              if (activeDonations.isNotEmpty) ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      context.tr('active_rescues'),
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppTheme.textPrimary, letterSpacing: -0.2),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: AppTheme.space4),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryGreen.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                      ),
                      child: Text(
                        '${activeDonations.length} ${context.tr('in_progress')}',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.primaryGreen),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space12),
                ...activeDonations.map((item) => DonationCard(
                      donation: item,
                      currentRole: 'donor',
                      onTap: () => context.push('/donor/detail/${item.id}'),
                    )),
                const SizedBox(height: AppTheme.space20),
              ],

              // ── 3. RECENT DONATIONS LIST ──────────────────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    context.tr('donation_history'),
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppTheme.textPrimary, letterSpacing: -0.2),
                  ),
                  if (donations.isNotEmpty)
                    TextButton(
                      onPressed: () => context.push('/donor/history'),
                      child: Text(context.tr('view_all'), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                    ),
                ],
              ),
              const SizedBox(height: AppTheme.space8),

              if (donationProv.isLoading && donations.isEmpty)
                const Column(
                  children: [
                    DonationCardSkeleton(),
                    DonationCardSkeleton(),
                  ],
                )
              else if (donationProv.errorMessage != null && donations.isEmpty)
                ErrorStateWidget(
                  message: ErrorStateWidget.formatErrorMessage(context, donationProv.errorMessage),
                  onRetry: _loadData,
                )
              else if (donations.isEmpty)
                EmptyStateWidget(
                  icon: Icons.fastfood_outlined,
                  title: context.tr('no_donations'),
                  description: context.tr('no_donations_desc'),
                  actionLabel: context.tr('donate_now').toUpperCase(),
                  onAction: () => context.push('/donor/create'),
                )
              else
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: donations.take(5).length,
                  itemBuilder: (context, index) {
                    final item = donations[index];
                    return DonationCard(
                      donation: item,
                      currentRole: 'donor',
                      onTap: () => context.push('/donor/detail/${item.id}'),
                    );
                  },
                ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(currentRole: 'donor', currentIndex: 0),
    );
  }

  Widget _buildNavChip({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppTheme.radiusPill),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: color),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImpactMetric(String value, String label, IconData icon, Color color) {
    return Column(
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: 4),
            Text(
              value,
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
          ],
        ),
        const SizedBox(height: 3),
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            color: AppTheme.textSecondary,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}
