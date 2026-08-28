import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../models/admin_operations_model.dart';
import '../../providers/admin_provider.dart';
import '../../widgets/skeleton_loader.dart';
import '../../widgets/role_bottom_nav.dart';
import 'admin_rescue_detail_modal.dart';

/// Administrator — Food Rescue Operations Control Center.
/// Action-oriented operational dashboard answering: "WHAT NEEDS MY ATTENTION RIGHT NOW?"
class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
  }

  Future<void> _loadData() async {
    final adminProv = Provider.of<AdminProvider>(context, listen: false);
    await Future.wait([
      adminProv.fetchReceivingSummary(),
      adminProv.fetchReceivingList(tab: 'ALL'),
      adminProv.fetchNgoCapacities(),
      adminProv.fetchCategoryBreakdown(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);
    final summary = adminProv.receivingSummary;
    final items = adminProv.receivingItems;
    final ngoCapacities = adminProv.ngoCapacities;
    final isLoading = adminProv.isReceivingLoading;
    final errorMessage = adminProv.errorMessage;

    // Filter actionable items for NEEDS ATTENTION section
    final needsAttentionItems = items.where((d) {
      final isCritical = d.rescueUrgencyLevel.toUpperCase() == 'CRITICAL';
      final isNearExpiryNoVolunteer = (d.remainingMinutes != null && d.remainingMinutes! <= 30 && d.assignedVolunteerId == null && d.status != 'completed');
      final isDelayed = (d.etaMinutes != null && d.remainingMinutes != null && d.etaMinutes! > d.remainingMinutes! && d.status != 'completed');
      final isFailed = ['pickup_failed', 'delivery_failed'].contains(d.status.toLowerCase());
      final hasMismatch = d.hasQuantityMismatch;
      final hasIssues = d.issueCount > 0;
      final needsInspection = d.aiVisualCondition.toUpperCase() == 'NEEDS_INSPECTION';

      return isCritical || isNearExpiryNoVolunteer || isDelayed || isFailed || hasMismatch || hasIssues || needsInspection;
    }).toList();

    // Filter active live rescues
    final liveRescues = items.where((d) =>
      ['accepted', 'assigned', 'on_the_way', 'arrived', 'collected', 'in_transit'].contains(d.status.toLowerCase())
    ).toList();

    // Filter recent receiving / completed items
    final recentReceiving = items.where((d) =>
      ['delivered', 'received', 'partially_distributed', 'completed'].contains(d.status.toLowerCase()) || d.hasQuantityMismatch
    ).take(5).toList();

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('role_admin'),
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, letterSpacing: -0.2),
            ),
            Text(
              context.tr('food_rescue_operations'),
              style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: context.tr('notifications_title'),
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () => context.push('/notifications'),
          ),
          IconButton(
            tooltip: context.tr('nav_profile'),
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      bottomNavigationBar: const RoleBottomNav(currentRole: 'admin', currentIndex: 0),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: isLoading && items.isEmpty
            ? _buildLoadingSkeleton()
            : errorMessage != null && items.isEmpty
                ? _buildErrorState()
                : SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ── 1. COMPACT OPERATIONAL SUMMARY STRIP ──
                        _buildCompactOperationalStrip(summary),
                        const SizedBox(height: AppTheme.space16),

                        // ── 2. PRIMARY SECTION: NEEDS YOUR ATTENTION ──
                        _buildNeedsAttentionSection(needsAttentionItems),
                        const SizedBox(height: AppTheme.space20),

                        // ── 3. LIVE RESCUES SECTION ──
                        _buildLiveRescuesSection(liveRescues),
                        const SizedBox(height: AppTheme.space20),

                        // ── 4. FOOD RECEIVING & DISTRIBUTION SECTION ──
                        _buildFoodReceivingSection(summary, recentReceiving),
                        const SizedBox(height: AppTheme.space20),

                        // ── 5. NGO INTAKE CAPACITY SECTION ──
                        if (ngoCapacities.isNotEmpty) ...[
                          _buildNgoCapacitySection(ngoCapacities),
                          const SizedBox(height: AppTheme.space20),
                        ],

                        // ── 6. QUICK ACTIONS (4 COMPACT TILES) ──
                        _buildQuickActionsGrid(),
                        const SizedBox(height: AppTheme.space24),
                      ],
                    ),
                  ),
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 1. COMPACT OPERATIONAL SUMMARY STRIP
  // ════════════════════════════════════════════════════════════════════════════
  Widget _buildCompactOperationalStrip(AdminReceivingSummaryModel? summary) {
    final active = summary?.activeRescues ?? 0;
    final urgent = summary?.urgentRescues ?? 0;
    final atRisk = summary?.criticalRescues ?? 0;
    final inTransit = summary?.inTransit ?? 0;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildCompactMetricItem('$active', context.tr('stat_active'), AppTheme.primaryGreen),
          _buildStripDivider(),
          _buildCompactMetricItem('$urgent', context.tr('stat_urgent'), const Color(0xFFD97706)),
          _buildStripDivider(),
          _buildCompactMetricItem('$atRisk', context.tr('stat_at_risk'), AppTheme.error),
          _buildStripDivider(),
          _buildCompactMetricItem('$inTransit', context.tr('stat_in_transit'), const Color(0xFF0284C7)),
        ],
      ),
    );
  }

  Widget _buildCompactMetricItem(String value, String label, Color color) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 7,
              height: 7,
              margin: const EdgeInsets.only(right: 5),
              decoration: BoxDecoration(shape: BoxShape.circle, color: color),
            ),
            Text(
              value,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: color,
                letterSpacing: -0.3,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: AppTheme.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildStripDivider() {
    return Container(
      width: 1,
      height: 24,
      color: AppTheme.border.withValues(alpha: 0.8),
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 2. PRIMARY SECTION: NEEDS YOUR ATTENTION
  // ════════════════════════════════════════════════════════════════════════════
  Widget _buildNeedsAttentionSection(List<AdminReceivingItemModel> attentionItems) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: attentionItems.isNotEmpty ? AppTheme.error.withValues(alpha: 0.12) : AppTheme.primaryGreen.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    attentionItems.isNotEmpty ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
                    size: 14,
                    color: attentionItems.isNotEmpty ? AppTheme.error : AppTheme.primaryGreen,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${attentionItems.length}',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: attentionItems.isNotEmpty ? AppTheme.error : AppTheme.primaryGreen,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Text(
              context.tr('needs_attention'),
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w800,
                color: AppTheme.textPrimary,
                letterSpacing: 0.3,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),

        if (attentionItems.isEmpty)
          _buildAllClearCard()
        else
          Column(
            children: attentionItems.take(4).map((item) => _buildAttentionCard(item)).toList(),
          ),
      ],
    );
  }

  Widget _buildAllClearCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.primaryGreen.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppTheme.primaryGreen.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.check_rounded, color: AppTheme.primaryGreen, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.tr('all_normal_title'),
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.primaryDark),
                ),
                const SizedBox(height: 2),
                Text(
                  context.tr('all_normal_subtitle'),
                  style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAttentionCard(AdminReceivingItemModel item) {
    final isCritical = item.rescueUrgencyLevel.toUpperCase() == 'CRITICAL';
    final hasMismatch = item.hasQuantityMismatch;
    final isDelayed = item.etaMinutes != null && item.remainingMinutes != null && item.etaMinutes! > item.remainingMinutes!;
    final noVolunteer = item.assignedVolunteerId == null && item.status != 'completed';

    Color bannerColor = const Color(0xFFD97706); // Amber default
    String issueTag = context.tr('stat_urgent');
    String problemDesc = '';
    String actionLabel = context.tr('btn_review');

    if (isCritical || (item.remainingMinutes != null && item.remainingMinutes! <= 20)) {
      bannerColor = AppTheme.error;
      issueTag = '🔴 ${context.tr('critical_rescue')}';
      problemDesc = noVolunteer ? context.tr('no_volunteer_assigned') : '${item.remainingMinutes ?? 15}m rescue window remaining';
      actionLabel = context.tr('btn_intervene');
    } else if (isDelayed) {
      bannerColor = const Color(0xFFEA580C);
      issueTag = '🟠 ${context.tr('delivery_delayed')}';
      problemDesc = 'ETA (${item.etaMinutes?.toStringAsFixed(0)}m) exceeds advisory window (${item.remainingMinutes ?? 0}m)';
      actionLabel = context.tr('btn_view');
    } else if (hasMismatch) {
      bannerColor = const Color(0xFFD97706);
      issueTag = '🟠 ${context.tr('quantity_mismatch')}';
      problemDesc = '${item.expectedQuantity.toStringAsFixed(0)} expected • ${item.receivedQuantity?.toStringAsFixed(0) ?? 0} received';
      actionLabel = context.tr('btn_review');
    } else if (item.issueCount > 0) {
      bannerColor = const Color(0xFFEA580C);
      issueTag = '🟠 ${context.tr('nav_issues')} (${item.issueCount})';
      problemDesc = 'Participant reported operational concern';
      actionLabel = context.tr('btn_review');
    } else {
      problemDesc = '${item.remainingMinutes ?? 30}m remaining';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: bannerColor.withValues(alpha: 0.35), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: bannerColor.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
          onTap: () => AdminRescueDetailModal.show(context, item.id),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Tag Row
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: bannerColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        issueTag,
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: bannerColor),
                      ),
                    ),
                    if (item.remainingMinutes != null && item.remainingMinutes! > 0)
                      Text(
                        '${item.remainingMinutes}m remaining',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: item.remainingMinutes! <= 30 ? AppTheme.error : AppTheme.textSecondary,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 8),

                // Food Details & Problem Row
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${item.foodName} • ${item.quantity.toStringAsFixed(0)} ${item.quantityUnit}',
                            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AppTheme.textPrimary),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            problemDesc,
                            style: TextStyle(fontSize: 12, color: bannerColor, fontWeight: FontWeight.w600),
                          ),
                          if (item.ngoName != null) ...[
                            const SizedBox(height: 2),
                            Text(
                              'NGO: ${item.ngoName}',
                              style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Prominent Action Button
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: bannerColor,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                        minimumSize: const Size(80, 36),
                        elevation: 0,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: () => AdminRescueDetailModal.show(context, item.id),
                      child: Text(
                        actionLabel,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 3. LIVE RESCUES SECTION
  // ════════════════════════════════════════════════════════════════════════════
  Widget _buildLiveRescuesSection(List<AdminReceivingItemModel> liveRescues) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              context.tr('live_rescues'),
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppTheme.textPrimary, letterSpacing: -0.2),
            ),
            TextButton(
              onPressed: () => context.go('/admin/donations'),
              child: Text(
                '${context.tr('view_all')} (${liveRescues.length})',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),

        if (liveRescues.isEmpty)
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.card,
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline, color: AppTheme.textSecondary, size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    context.tr('no_food_in_transit'),
                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                  ),
                ),
              ],
            ),
          )
        else
          Container(
            decoration: BoxDecoration(
              color: AppTheme.card,
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              border: Border.all(color: AppTheme.border),
            ),
            child: ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: liveRescues.take(4).length,
              separatorBuilder: (_, __) => const Divider(height: 1, color: AppTheme.border),
              itemBuilder: (context, index) {
                final item = liveRescues[index];
                return _buildLiveRescueRow(item);
              },
            ),
          ),
      ],
    );
  }

  Widget _buildLiveRescueRow(AdminReceivingItemModel item) {
    final stageText = _getFriendlyStageText(item.status);
    final isUrgent = item.rescueUrgencyLevel.toUpperCase() == 'URGENT' || item.rescueUrgencyLevel.toUpperCase() == 'CRITICAL';
    final etaText = item.etaMinutes != null ? '${item.etaMinutes!.toStringAsFixed(0)} min' : (item.remainingMinutes != null ? '${item.remainingMinutes} min' : '--');

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => AdminRescueDetailModal.show(context, item.id),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: isUrgent ? const Color(0xFFD97706).withValues(alpha: 0.12) : AppTheme.primaryGreen.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.two_wheeler_rounded,
                  size: 16,
                  color: isUrgent ? const Color(0xFFD97706) : AppTheme.primaryGreen,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${item.foodName} • ${item.quantity.toStringAsFixed(0)} ${item.quantityUnit}',
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '$stageText • ${item.volunteerName ?? "Unassigned"}',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: isUrgent ? AppTheme.error.withValues(alpha: 0.1) : AppTheme.primaryGreen.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      isUrgent ? context.tr('stat_urgent') : context.tr('stat_active'),
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: isUrgent ? AppTheme.error : AppTheme.primaryDark,
                      ),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    etaText,
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _getFriendlyStageText(String status) {
    switch (status.toLowerCase()) {
      case 'accepted':
        return 'NGO Accepted';
      case 'assigned':
        return 'Courier Assigned';
      case 'on_the_way':
        return 'En Route to Donor';
      case 'arrived':
        return 'Arrived at Pickup';
      case 'collected':
      case 'in_transit':
        return 'In Transit to NGO';
      case 'delivered':
        return 'Arrived at NGO';
      default:
        return status;
    }
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 4. FOOD RECEIVING & DISTRIBUTION SECTION
  // ════════════════════════════════════════════════════════════════════════════
  Widget _buildFoodReceivingSection(AdminReceivingSummaryModel? summary, List<AdminReceivingItemModel> recentReceiving) {
    final received = summary?.receivedToday ?? 0.0;
    final distributed = summary?.distributedToday ?? 0.0;
    final remaining = summary?.remainingToday ?? 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              context.tr('food_receiving'),
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppTheme.textPrimary, letterSpacing: -0.2),
            ),
            Text(
              '${received.toStringAsFixed(0)} meals received today',
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.primaryGreen),
            ),
          ],
        ),
        const SizedBox(height: 8),

        // 5-Metric Receiving Breakdown Strip
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          decoration: BoxDecoration(
            color: AppTheme.card,
            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
            border: Border.all(color: AppTheme.border),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildReceivingStatItem(context.tr('stat_received'), received.toStringAsFixed(0), AppTheme.primaryGreen),
              _buildReceivingStatItem(context.tr('stat_distributed'), distributed.toStringAsFixed(0), const Color(0xFF0284C7)),
              _buildReceivingStatItem(context.tr('stat_remaining'), remaining.toStringAsFixed(0), const Color(0xFFD97706)),
            ],
          ),
        ),
        const SizedBox(height: 10),

        // Recent Receiving Records
        if (recentReceiving.isNotEmpty) ...[
          Text(
            context.tr('recent_receiving'),
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
          ),
          const SizedBox(height: 6),
          ...recentReceiving.map((item) => _buildRecentReceivingCard(item)),
        ],
      ],
    );
  }

  Widget _buildReceivingStatItem(String label, String value, Color color) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: color),
        ),
        const SizedBox(height: 1),
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.w500),
        ),
      ],
    );
  }

  Widget _buildRecentReceivingCard(AdminReceivingItemModel item) {
    final hasMismatch = item.hasQuantityMismatch;

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: hasMismatch ? const Color(0xFFD97706).withValues(alpha: 0.4) : AppTheme.border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.foodName,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: 2),
                Text(
                  '${item.expectedQuantity.toStringAsFixed(0)} expected • ${item.receivedQuantity?.toStringAsFixed(0) ?? item.quantity.toStringAsFixed(0)} received (${item.ngoName ?? "NGO Center"})',
                  style: TextStyle(
                    fontSize: 11,
                    color: hasMismatch ? const Color(0xFFD97706) : AppTheme.textSecondary,
                    fontWeight: hasMismatch ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
              ],
            ),
          ),
          if (hasMismatch) ...[
            const SizedBox(width: 8),
            TextButton(
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                minimumSize: const Size(60, 30),
                backgroundColor: const Color(0xFFD97706).withValues(alpha: 0.12),
              ),
              onPressed: () => AdminRescueDetailModal.show(context, item.id),
              child: Text(
                context.tr('btn_review'),
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFFD97706)),
              ),
            ),
          ] else ...[
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.chevron_right, size: 18, color: AppTheme.textSecondary),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
              onPressed: () => AdminRescueDetailModal.show(context, item.id),
            ),
          ],
        ],
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 5. NGO INTAKE CAPACITY SECTION
  // ════════════════════════════════════════════════════════════════════════════
  Widget _buildNgoCapacitySection(List<AdminNgoCapacityModel> ngoCapacities) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              context.tr('ngo_capacity'),
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppTheme.textPrimary, letterSpacing: -0.2),
            ),
            Text(
              '${ngoCapacities.length} Verified Centers',
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.textSecondary),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 88,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: ngoCapacities.take(5).length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (context, index) {
              final ngo = ngoCapacities[index];
              final availablePercent = 100 - (ngo.utilizationPercent).round();
              final isFull = ngo.remainingCapacity <= 0 || availablePercent <= 5;
              final isWarning = availablePercent <= 30;

              final badgeColor = isFull ? AppTheme.error : (isWarning ? const Color(0xFFD97706) : AppTheme.primaryGreen);

              return Container(
                width: 185,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: isFull ? AppTheme.error.withValues(alpha: 0.3) : AppTheme.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      ngo.organizationName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            isFull ? context.tr('capacity_full') : '$availablePercent% remaining',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              color: badgeColor,
                            ),
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${ngo.remainingCapacity.toStringAsFixed(0)} meals',
                          style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary),
                        ),
                      ],
                    ),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(3),
                      child: LinearProgressIndicator(
                        value: (ngo.utilizationPercent / 100).clamp(0.0, 1.0),
                        backgroundColor: AppTheme.border,
                        valueColor: AlwaysStoppedAnimation<Color>(badgeColor),
                        minHeight: 4,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 6. QUICK ACTIONS GRID (4 COMPACT ACTIONS)
  // ════════════════════════════════════════════════════════════════════════════
  Widget _buildQuickActionsGrid() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr('quick_actions'),
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppTheme.textPrimary, letterSpacing: -0.2),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _buildQuickActionTile(
                icon: Icons.local_shipping_outlined,
                label: context.tr('nav_rescues'),
                color: AppTheme.primaryGreen,
                onTap: () => context.go('/admin/donations'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildQuickActionTile(
                icon: Icons.inventory_2_outlined,
                label: context.tr('nav_receiving'),
                color: const Color(0xFF0284C7),
                onTap: () => context.go('/admin/donations'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _buildQuickActionTile(
                icon: Icons.report_problem_outlined,
                label: context.tr('nav_issues'),
                color: const Color(0xFFD97706),
                onTap: () => context.push('/admin/disputes'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildQuickActionTile(
                icon: Icons.verified_user_outlined,
                label: context.tr('verify_ngo_btn'),
                color: const Color(0xFF7C3AED),
                onTap: () => context.push('/admin/verify-ngos'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildQuickActionTile({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Material(
      color: AppTheme.card,
      borderRadius: BorderRadius.circular(AppTheme.radiusCard),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
            border: Border.all(color: AppTheme.border),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(7),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, size: 18, color: color),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
              ),
              const Icon(Icons.chevron_right, size: 16, color: AppTheme.textSecondary),
            ],
          ),
        ),
      ),
    );
  }

  // ════════════════════════════════════════════════════════════════════════════
  // SKELETON LOADING & ERROR STATES
  // ════════════════════════════════════════════════════════════════════════════
  Widget _buildLoadingSkeleton() {
    return const SingleChildScrollView(
      padding: EdgeInsets.all(AppTheme.space16),
      child: Column(
        children: [
          DonationCardSkeleton(),
          SizedBox(height: 12),
          DonationCardSkeleton(),
          SizedBox(height: 12),
          DonationCardSkeleton(),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.space24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_rounded, size: 48, color: AppTheme.error),
            const SizedBox(height: 12),
            Text(
              context.tr('unable_to_load_operations'),
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryGreen,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              ),
              icon: const Icon(Icons.refresh, size: 18),
              label: Text(context.tr('retry')),
              onPressed: _loadData,
            ),
          ],
        ),
      ),
    );
  }
}
