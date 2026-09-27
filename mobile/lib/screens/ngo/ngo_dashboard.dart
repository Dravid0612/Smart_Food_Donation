import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/donation_provider.dart';
import '../../providers/notification_provider.dart';
import '../../providers/ngo_provider.dart';
import '../../widgets/donation_card.dart';
import '../../widgets/rescue_checklist_widget.dart';
import '../../widgets/skeleton_loader.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/error_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';

/// NGO Feed & Dashboard focusing on available surplus food items with 1-tap Accept/Reject.
class NgoDashboardScreen extends StatefulWidget {
  const NgoDashboardScreen({super.key});

  @override
  State<NgoDashboardScreen> createState() => _NgoDashboardScreenState();
}

class _NgoDashboardScreenState extends State<NgoDashboardScreen> {
  int _selectedTab = 0; // 0: Available Surplus, 1: In-Transit, 2: Delivered
  String _filterSubcategory = 'All'; // All, Urgent, Critical, High Match, Bulk

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
    final ngoProv = Provider.of<NgoProvider>(context, listen: false);
    await Future.wait([
      donationProv.fetchDonations(),
      notifProv.fetchNotifications(),
      ngoProv.fetchMyNgo(),
    ]);
  }

  Future<void> _executeAccept(int donationId, String pickupMode) async {
    final prov = Provider.of<DonationProvider>(context, listen: false);
    final ok = await prov.acceptDonation(donationId, pickupMode: pickupMode);
    if (!mounted) return;
    if (ok) {
      final modeName = pickupMode == 'self_pickup'
          ? context.tr('collect_yourself')
          : context.tr('request_volunteer_btn');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$modeName: ${context.tr('accept_rescue')}! 🎉'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
      _loadData();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(prov.errorMessage != null ? context.trError(prov.errorMessage!) : context.trError('err_server')),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  void _showAcceptMethodSheet(int donationId, String foodName) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.card,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusFeatureCard)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppTheme.space20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Text(
                context.tr('ngo_accept_choice_title'),
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                context.tr('ngo_accept_choice_desc'),
                style: const TextStyle(
                  fontSize: 13,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 20),
              // Option 1: COLLECT YOURSELF
              InkWell(
                onTap: () {
                  Navigator.pop(ctx);
                  _executeAccept(donationId, 'self_pickup');
                },
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                child: Container(
                  padding: const EdgeInsets.all(AppTheme.space16),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryGreen.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                    border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryGreen.withValues(alpha: 0.15),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.directions_car, color: AppTheme.primaryGreen, size: 24),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              context.tr('collect_yourself'),
                              style: const TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.primaryGreen,
                              ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              context.tr('collect_yourself_desc'),
                              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right, color: AppTheme.primaryGreen),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              // Option 2: REQUEST VOLUNTEER
              InkWell(
                onTap: () {
                  Navigator.pop(ctx);
                  _executeAccept(donationId, 'volunteer_dispatch');
                },
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                child: Container(
                  padding: const EdgeInsets.all(AppTheme.space16),
                  decoration: BoxDecoration(
                    color: AppTheme.secondaryTerracotta.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                    border: Border.all(color: AppTheme.secondaryTerracotta.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppTheme.secondaryTerracotta.withValues(alpha: 0.15),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.delivery_dining, color: AppTheme.secondaryTerracotta, size: 24),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              context.tr('request_volunteer_btn'),
                              style: const TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.secondaryTerracotta,
                              ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              context.tr('request_volunteer_desc'),
                              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right, color: AppTheme.secondaryTerracotta),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _handleReject(int donationId) async {
    final prov = Provider.of<DonationProvider>(context, listen: false);
    final ok = await prov.rejectDonation(donationId);
    if (!mounted) return;
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('pass'))),
      );
      _loadData();
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final donationProv = Provider.of<DonationProvider>(context);
    final notifProv = Provider.of<NotificationProvider>(context);

    final user = auth.currentUser;
    final allDonations = donationProv.donations;

    final pendingDonations = allDonations.where((d) => d.status.toLowerCase() == 'pending').toList();
    final urgentCount = pendingDonations.where((d) {
      final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
      return urg == 'URGENT';
    }).length;
    final criticalCount = pendingDonations.where((d) {
      final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
      return urg == 'CRITICAL';
    }).length;

    var availableDonations = List.of(pendingDonations);
    if (_filterSubcategory == 'Urgent') {
      availableDonations = availableDonations.where((d) {
        final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
        return urg == 'URGENT';
      }).toList();
    } else if (_filterSubcategory == 'Critical') {
      availableDonations = availableDonations.where((d) {
        final urg = (d.rescueUrgencyLevel.isNotEmpty ? d.rescueUrgencyLevel : d.urgencyLevel).toUpperCase();
        return urg == 'CRITICAL';
      }).toList();
    } else if (_filterSubcategory == 'High Match') {
      availableDonations = availableDonations.where((d) => (d.conditionScore ?? 0) >= 80).toList();
    } else if (_filterSubcategory == 'Bulk') {
      availableDonations = availableDonations.where((d) => d.quantity >= 50).toList();
    }

    final inTransitDonations = allDonations.where((d) => ['accepted', 'volunteer_assigned', 'collected'].contains(d.status.toLowerCase())).toList();
    final completedDonations = allDonations.where((d) => ['completed', 'delivered'].contains(d.status.toLowerCase())).toList();

    // ── N1 Verification Pending Special Entry State ─────────────────────────
    final ngoProv = Provider.of<NgoProvider>(context);
    final isPendingVerification = (ngoProv.myNgo != null && !ngoProv.myNgo!.isVerified);
    if (isPendingVerification) {
      return _buildVerificationPendingScreen(context, user);
    }

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              user?.name ?? context.tr('role_ngo'),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              overflow: TextOverflow.ellipsis,
            ),
            Row(
              children: [
                const Icon(Icons.verified, size: 13, color: AppTheme.primaryGreen),
                const SizedBox(width: 4),
                Text(context.tr('verified_partner'), style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: context.tr('food_category'),
            icon: const Icon(Icons.tune, color: AppTheme.primaryGreen),
            onPressed: () => context.push('/ngo/requirements'),
          ),
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
                    decoration: const BoxDecoration(color: AppTheme.error, shape: BoxShape.circle),
                    child: Text('${notifProv.unreadCount}', style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
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
              // ── 1. RECEIVING CAPACITY & DEMAND STRIP ─────────────────────
              Container(
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
                        Text(
                          context.tr('capacity_kg'),
                          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                        ),
                        TextButton.icon(
                          onPressed: () => context.push('/ngo/requirements'),
                          icon: const Icon(Icons.edit_note, size: 16),
                          label: Text(context.tr('food_category')),
                          style: TextButton.styleFrom(
                            foregroundColor: AppTheme.primaryGreen,
                            padding: EdgeInsets.zero,
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppTheme.space8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: const LinearProgressIndicator(
                        value: 0.45,
                        minHeight: 8,
                        backgroundColor: AppTheme.background,
                        valueColor: AlwaysStoppedAnimation<Color>(AppTheme.primaryGreen),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),

              // ── 2. SEGMENTED TABS & SUB-FILTER CHIPS ───────────────────────
              SegmentedButton<int>(
                segments: [
                  ButtonSegment(
                    value: 0,
                    label: Text('${context.tr('active_rescues')} (${availableDonations.length})'),
                    icon: const Icon(Icons.fastfood_outlined, size: 16),
                  ),
                  ButtonSegment(
                    value: 1,
                    label: Text('${context.tr('in_progress')} (${inTransitDonations.length})'),
                    icon: const Icon(Icons.local_shipping_outlined, size: 16),
                  ),
                  ButtonSegment(
                    value: 2,
                    label: Text('${context.tr('status_delivered')} (${completedDonations.length})'),
                    icon: const Icon(Icons.done_all, size: 16),
                  ),
                ],
                selected: {_selectedTab},
                onSelectionChanged: (set) => setState(() => _selectedTab = set.first),
                style: ButtonStyle(
                  backgroundColor: WidgetStateProperty.resolveWith<Color>((states) {
                    if (states.contains(WidgetState.selected)) {
                      return AppTheme.primaryGreen.withValues(alpha: 0.12);
                    }
                    return AppTheme.card;
                  }),
                ),
              ),
              const SizedBox(height: AppTheme.space12),

              if (_selectedTab == 0) ...[
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildFilterChip('All', 'All (${pendingDonations.length})', Icons.dashboard_outlined),
                      const SizedBox(width: 8),
                      _buildFilterChip('Urgent', '⚡ ${context.tr("proactive_tab_urgent")} ($urgentCount)', Icons.bolt,
                          color: AppTheme.secondaryTerracotta, count: urgentCount),
                      const SizedBox(width: 8),
                      _buildFilterChip('Critical', '🚨 ${context.tr("proactive_tab_critical")} ($criticalCount)', Icons.emergency,
                          color: AppTheme.error, count: criticalCount),
                      const SizedBox(width: 8),
                      _buildFilterChip('High Match', '★ ${context.tr("why_this_match")}', Icons.star_outline),
                      const SizedBox(width: 8),
                      _buildFilterChip('Bulk', '📦 Bulk (50+)', Icons.inventory_2_outlined),
                    ],
                  ),
                ),
                const SizedBox(height: AppTheme.space12),
              ],

              // ── 3. DONATIONS FEED ─────────────────────────────────────────
              if (donationProv.isLoading && allDonations.isEmpty)
                const Column(
                  children: [
                    DonationCardSkeleton(),
                    DonationCardSkeleton(),
                  ],
                )
              else if (donationProv.errorMessage != null && allDonations.isEmpty)
                ErrorStateWidget(
                  message: ErrorStateWidget.formatErrorMessage(context, donationProv.errorMessage),
                  onRetry: _loadData,
                )
              else
                _buildTabContent(
                  _selectedTab == 0
                      ? availableDonations
                      : _selectedTab == 1
                          ? inTransitDonations
                          : completedDonations,
                  tabIndex: _selectedTab,
                ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(currentRole: 'ngo', currentIndex: 0),
    );
  }

  Widget _buildTabContent(List donations, {required int tabIndex}) {
    if (donations.isEmpty) {
      if (tabIndex == 0) {
        return EmptyStateWidget(
          icon: Icons.inbox_outlined,
          title: context.tr('no_donations'),
          description: context.tr('no_donations_desc'),
        );
      } else if (tabIndex == 1) {
        return EmptyStateWidget(
          icon: Icons.local_shipping_outlined,
          title: context.tr('no_active_deliveries'),
          description: context.tr('in_progress'),
        );
      } else {
        return EmptyStateWidget(
          icon: Icons.check_circle_outline,
          title: context.tr('no_donations'),
          description: context.tr('status_completed'),
        );
      }
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: donations.length,
      itemBuilder: (context, index) {
        final item = donations[index];
        final isAvailable = tabIndex == 0;
        final isCollected = item.status.toLowerCase() == 'collected';

        return Column(
          children: [
            DonationCard(
              donation: item,
              currentRole: 'ngo',
              locationText: isAvailable
                  ? '📍 ${(item.currentDistanceKm ?? 2.4).toStringAsFixed(1)} km • (Masked)'
                  : item.pickupAddress,
              donorTrustLabel: context.tr('verified_partner'),
              isVerifiedDonor: true,
              acceptLabel: context.tr('accept_rescue'),
              rejectLabel: context.tr('pass'),
              onTap: () => context.push('/donor/detail/${item.id}'),
              onAccept: isAvailable ? () => _showAcceptMethodSheet(item.id, item.foodName) : null,
              onReject: isAvailable ? () => _handleReject(item.id) : null,
              trailingAction: isCollected
                  ? ElevatedButton.icon(
                      onPressed: () => context.push('/ngo/receiving/${item.id}'),
                      icon: const Icon(Icons.check, size: 16),
                      label: Text(context.tr('confirm')),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryGreen,
                        padding: const EdgeInsets.symmetric(horizontal: AppTheme.space12, vertical: AppTheme.space8),
                      ),
                    )
                  : item.status.toLowerCase() == 'delivered'
                      ? ElevatedButton.icon(
                          onPressed: () => context.push('/ngo/distribution/${item.id}'),
                          icon: const Icon(Icons.restaurant_outlined, size: 16),
                          label: Text(context.tr('distribute_meals')),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryGreen,
                            padding: const EdgeInsets.symmetric(horizontal: AppTheme.space12, vertical: AppTheme.space8),
                          ),
                        )
                      : null,
            ),
            if (isAvailable) ...[
              Padding(
                padding: const EdgeInsets.only(bottom: AppTheme.space12),
                child: RescueChecklistWidget(
                  demandMatched: true,
                  ngoOpen: true,
                  capacityAvailable: true,
                  volunteerTransitFit: item.quantity <= 100,
                  expiryWindow: context.tr('rescue_window'),
                  isTightDeadline: item.urgencyLevel == 'Urgent',
                ),
              ),
            ] else if (tabIndex == 1) ...[
              Padding(
                padding: const EdgeInsets.only(bottom: AppTheme.space12),
                child: Container(
                  padding: const EdgeInsets.all(AppTheme.space12),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceWarm,
                    borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                    border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.directions_bike_rounded, color: AppTheme.primaryGreen, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          item.currentEtaMinutes != null
                              ? '${context.tr('ngo_arrival_eta')}: ${item.currentEtaMinutes!.toInt()} min (${context.tr('tracking_eta_label')})'
                              : '${context.tr('assigned_volunteer')}: ${item.volunteerName ?? context.tr("in_progress")}',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                        ),
                      ),
                      if (item.isRematched)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppTheme.info.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            context.tr('status_rematched'),
                            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.info),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        );
      },
    );
  }

  Widget _buildFilterChip(String key, String label, IconData icon, {Color? color, int count = 0}) {
    final isSelected = _filterSubcategory == key;
    final chipColor = color ?? AppTheme.primaryGreen;

    return InkWell(
      onTap: () => setState(() => _filterSubcategory = key),
      borderRadius: BorderRadius.circular(AppTheme.radiusPill),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? chipColor.withValues(alpha: 0.15) : AppTheme.card,
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          border: Border.all(
            color: isSelected ? chipColor : AppTheme.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: isSelected ? chipColor : AppTheme.textSecondary),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                color: isSelected ? chipColor : AppTheme.textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// N1 Verification Pending Screen (No rescue actions available)
  Widget _buildVerificationPendingScreen(BuildContext context, dynamic user) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              user?.name ?? context.tr('role_ngo'),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              overflow: TextOverflow.ellipsis,
            ),
            Row(
              children: [
                const Icon(Icons.hourglass_empty, size: 13, color: AppTheme.urgentAmber),
                const SizedBox(width: 4),
                Text(
                  context.tr('status_pending'),
                  style: const TextStyle(fontSize: 11, color: AppTheme.urgentAmber, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: context.tr('refresh'),
            onPressed: _loadData,
          ),
          IconButton(
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: AppTheme.space24, vertical: AppTheme.space32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 96,
                height: 96,
                decoration: BoxDecoration(
                  color: AppTheme.urgentAmber.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                  border: Border.all(color: AppTheme.urgentAmber.withValues(alpha: 0.3), width: 2),
                ),
                child: const Icon(
                  Icons.verified_user_outlined,
                  size: 48,
                  color: AppTheme.urgentAmber,
                ),
              ),
              const SizedBox(height: AppTheme.space24),
              Text(
                context.tr('verification_pending_title'),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                  height: 1.3,
                ),
              ),
              const SizedBox(height: AppTheme.space12),
              Text(
                context.tr('verification_pending_desc'),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 15,
                  color: AppTheme.textSecondary,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: AppTheme.space32),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    showDialog(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: Text(context.tr('support_dialog_title')),
                        content: Text(context.tr('support_dialog_desc')),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(ctx),
                            child: Text(context.tr('close')),
                          ),
                        ],
                      ),
                    );
                  },
                  icon: const Icon(Icons.support_agent, color: Colors.white),
                  label: Text(
                    context.tr('contact_support').toUpperCase(),
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.trustTeal,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(currentRole: 'ngo', currentIndex: 0),
    );
  }
}
