import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/localization/app_locale.dart';
import '../../models/performance_model.dart';
import '../../providers/admin_provider.dart';

class AdminPerformanceScreen extends StatefulWidget {
  const AdminPerformanceScreen({super.key});

  @override
  State<AdminPerformanceScreen> createState() => _AdminPerformanceScreenState();
}

class _AdminPerformanceScreenState extends State<AdminPerformanceScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  String? _errorMessage;

  AdminPerformanceOverview? _overview;
  RescueFailureAnalytics? _failures;
  List<NeedsReviewParticipant> _needsReviewList = [];
  List<SuspiciousFeedbackAlert> _suspiciousAlerts = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final adminProv = Provider.of<AdminProvider>(context, listen: false);
    try {
      final overview = await adminProv.fetchPerformanceOverview();
      final failures = await adminProv.fetchFailureAnalytics();
      final needsReview = await adminProv.fetchNeedsReviewQueue();
      final suspicious = await adminProv.fetchSuspiciousFeedbackAlerts();

      if (mounted) {
        setState(() {
          _overview = overview;
          _failures = failures;
          _needsReviewList = needsReview;
          _suspiciousAlerts = suspicious;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _executeAction(
    int userId,
    String action,
    String userName,
  ) async {
    final noteController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Execute $action'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Target: $userName (ID: $userId)'),
            const SizedBox(height: 12),
            TextField(
              controller: noteController,
              decoration: InputDecoration(
                labelText: 'Administrative Notes / Justification',
                hintText: ctx.tr('admin_notes_hint'),
                border: const OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(ctx.tr('cancel')),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: action == 'RESTORE' ? Colors.green : Colors.red.shade700,
              foregroundColor: Colors.white,
            ),
            child: Text(ctx.tr('confirm')),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      if (!mounted) return;
      final adminProv = Provider.of<AdminProvider>(context, listen: false);
      final success = await adminProv.executePerformanceAction(
        userId: userId,
        action: action,
        notes: noteController.text.trim(),
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              success
                  ? 'Performance action $action applied successfully.'
                  : 'Failed to apply performance action.',
            ),
          ),
        );
        _loadData();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('admin_performance_hub')),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
            tooltip: context.tr('refresh'),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: [
            Tab(icon: const Icon(Icons.dashboard_outlined), text: context.tr('system_stats')),
            Tab(icon: const Icon(Icons.analytics_outlined), text: context.tr('failure_analytics_title')),
            Tab(
              icon: Badge(
                label: Text('${_needsReviewList.length}'),
                isLabelVisible: _needsReviewList.isNotEmpty,
                child: const Icon(Icons.flag_outlined),
              ),
              text: context.tr('needs_review_queue'),
            ),
            Tab(
              icon: Badge(
                label: Text('${_suspiciousAlerts.length}'),
                isLabelVisible: _suspiciousAlerts.isNotEmpty,
                child: const Icon(Icons.security),
              ),
              text: context.tr('suspicious_feedback_title'),
            ),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline, size: 48, color: Colors.red.shade400),
                      const SizedBox(height: 12),
                      Text(_errorMessage!),
                      const SizedBox(height: 12),
                      ElevatedButton(
                        onPressed: _loadData,
                        child: Text(context.tr('retry')),
                      ),
                    ],
                  ),
                )
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildOverviewTab(),
                    _buildFailureAnalyticsTab(),
                    _buildNeedsReviewTab(),
                    _buildSuspiciousFeedbackTab(),
                  ],
                ),
    );
  }

  Widget _buildOverviewTab() {
    final ov = _overview;
    if (ov == null) return const Center(child: Text('No data'));

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Network Success Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [Colors.teal.shade700, Colors.teal.shade900],
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Platform Rescue Success Rate',
                style: TextStyle(color: Colors.white70, fontSize: 13),
              ),
              const SizedBox(height: 4),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '${ov.overallRescueSuccessRatePercent.toStringAsFixed(1)}%',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white24,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${ov.totalActiveVolunteers} Active Couriers',
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        const SizedBox(height: 16),

        // Grid of Key Performance Indicators
        GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 10,
          mainAxisSpacing: 10,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 1.4,
          children: [
            _buildKpiTile(
              label: 'Avg Response Time',
              value: '${ov.averageVolunteerResponseTimeSeconds.toStringAsFixed(0)}s',
              icon: Icons.timer,
              color: Colors.blue,
            ),
            _buildKpiTile(
              label: 'Network On-Time',
              value: '${ov.networkOnTimeRatePercent.toStringAsFixed(1)}%',
              icon: Icons.access_time_filled,
              color: Colors.green,
            ),
            _buildKpiTile(
              label: 'Volunteer Acceptance',
              value: '${ov.volunteerAcceptanceRatePercent.toStringAsFixed(1)}%',
              icon: Icons.how_to_reg,
              color: Colors.orange,
            ),
            _buildKpiTile(
              label: 'Fallback Escalation',
              value: '${ov.fallbackEscalationRatePercent.toStringAsFixed(1)}%',
              icon: Icons.alt_route,
              color: Colors.purple,
            ),
            _buildKpiTile(
              label: 'Needs Review',
              value: '${ov.needsReviewCount}',
              icon: Icons.flag,
              color: ov.needsReviewCount > 0 ? Colors.red : Colors.grey,
            ),
            _buildKpiTile(
              label: 'Critical Incidents',
              value: '${ov.criticalAlertsCount}',
              icon: Icons.warning,
              color: ov.criticalAlertsCount > 0 ? Colors.red.shade800 : Colors.green,
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildKpiTile({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.02),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFailureAnalyticsTab() {
    final fa = _failures;
    if (fa == null || fa.failureReasons.isEmpty) {
      return const Center(child: Text('No failure events recorded. Excellent!'));
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Total Rescue Attempts: ${fa.totalRescueAttempts}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            Text(
              'Failed/Cancelled: ${fa.totalFailedOrCancelled}',
              style: TextStyle(color: Colors.red.shade700, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ...fa.failureReasons.map((item) {
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          item.reasonLabel,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ),
                      Text(
                        '${item.count} (${item.percentage.toStringAsFixed(1)}%)',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  LinearProgressIndicator(
                    value: (item.percentage / 100.0).clamp(0.0, 1.0),
                    backgroundColor: Colors.grey.shade200,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      item.percentage > 30.0 ? Colors.red : Colors.orange,
                    ),
                    minHeight: 6,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ],
              ),
            ),
          );
        }),
      ],
    );
  }

  Widget _buildNeedsReviewTab() {
    if (_needsReviewList.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle_outline, size: 64, color: Colors.green.shade400),
            const SizedBox(height: 12),
            const Text(
              'All participants in good operational standing.',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _needsReviewList.length,
      itemBuilder: (ctx, index) {
        final p = _needsReviewList[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: BorderSide(color: Colors.red.shade200),
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          p.name,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        Text(
                          'Role: ${p.role.toUpperCase()} • ID: ${p.userId}',
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                        ),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.red.shade300),
                      ),
                      child: Text(
                        p.adminActionStatus,
                        style: TextStyle(
                          color: Colors.red.shade800,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.amber.shade50,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    'Trigger: ${p.triggerReason}',
                    style: TextStyle(color: Colors.amber.shade900, fontSize: 12),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildStatItem('No-Show', '${p.noShowRatePercent.toStringAsFixed(0)}%'),
                    _buildStatItem('Completion', '${p.completionRatePercent.toStringAsFixed(0)}%'),
                    _buildStatItem('Cancellation', '${p.cancellationRatePercent.toStringAsFixed(0)}%'),
                    _buildStatItem('Score', '${p.overallReliabilityScore.toStringAsFixed(0)}%'),
                  ],
                ),
                const Divider(height: 16),
                // Action Buttons
                Wrap(
                  spacing: 6,
                  children: [
                    OutlinedButton(
                      onPressed: () => _executeAction(p.userId, 'MONITOR', p.name),
                      child: Text(context.tr('action_monitor')),
                    ),
                    OutlinedButton(
                      onPressed: () => _executeAction(p.userId, 'TEMPORARILY_DEPRIORITIZE', p.name),
                      style: OutlinedButton.styleFrom(foregroundColor: Colors.orange.shade800),
                      child: Text(context.tr('action_deprioritize')),
                    ),
                    ElevatedButton(
                      onPressed: () => _executeAction(p.userId, 'RESTORE', p.name),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green.shade700,
                        foregroundColor: Colors.white,
                      ),
                      child: Text(context.tr('action_restore')),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildStatItem(String label, String val) {
    return Column(
      children: [
        Text(val, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
        Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 10)),
      ],
    );
  }

  Widget _buildSuspiciousFeedbackTab() {
    if (_suspiciousAlerts.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.shield_outlined, size: 64, color: Colors.teal.shade400),
            const SizedBox(height: 12),
            const Text(
              'No suspicious rating patterns detected.',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _suspiciousAlerts.length,
      itemBuilder: (ctx, index) {
        final a = _suspiciousAlerts[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.warning_amber, color: Colors.orange, size: 18),
                        const SizedBox(width: 6),
                        Text(
                          'Pattern: ${a.suspicionReason.replaceAll('_', ' ').toUpperCase()}',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ],
                    ),
                    Chip(
                      label: Text(a.severity),
                      visualDensity: VisualDensity.compact,
                      backgroundColor: a.severity == 'HIGH' ? Colors.red.shade50 : Colors.orange.shade50,
                      labelStyle: TextStyle(
                        color: a.severity == 'HIGH' ? Colors.red.shade800 : Colors.orange.shade900,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  'Author: ${a.authorName} (${a.authorRole}) • Target: ${a.targetName ?? 'N/A'}',
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                ),
                if (a.comment != null) ...[
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '"${a.comment}"',
                      style: const TextStyle(fontStyle: FontStyle.italic, fontSize: 12),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
