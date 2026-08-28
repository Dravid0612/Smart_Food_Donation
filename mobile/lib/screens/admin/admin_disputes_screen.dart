import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/admin_provider.dart';
import '../../models/feedback_model.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';

/// Admin Screen for Feedback Overview & Operational Issues Intervention Queue.
class AdminDisputesScreen extends StatefulWidget {
  const AdminDisputesScreen({super.key});

  @override
  State<AdminDisputesScreen> createState() => _AdminDisputesScreenState();
}

class _AdminDisputesScreenState extends State<AdminDisputesScreen> {
  final String _selectedStatus = 'ALL';
  String _selectedSeverity = 'ALL';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
  }

  Future<void> _loadData() async {
    final adminProv = Provider.of<AdminProvider>(context, listen: false);
    await adminProv.fetchFeedbackOverview();
    await adminProv.fetchAdminIssues(
      status: _selectedStatus == 'ALL' ? null : _selectedStatus,
      severity: _selectedSeverity == 'ALL' ? null : _selectedSeverity,
    );
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return AppTheme.error;
      case 'HIGH':
        return const Color(0xFFEA580C); // Dark orange
      case 'MEDIUM':
        return const Color(0xFFD97706); // Amber
      case 'LOW':
      default:
        return const Color(0xFF0284C7); // Sky blue
    }
  }

  Color _getStatusColor(String status) {
    switch (status.toUpperCase()) {
      case 'OPEN':
        return AppTheme.error;
      case 'UNDER_REVIEW':
      case 'ACTION_REQUIRED':
        return const Color(0xFFD97706);
      case 'RESOLVED':
        return AppTheme.primaryGreen;
      case 'DISMISSED':
      default:
        return AppTheme.textSecondary;
    }
  }

  void _showResolveModal(BuildContext context, RescueIssueReportModel issue) {
    final notesController = TextEditingController();
    double penalty = 0.0;
    bool isSubmitting = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => AlertDialog(
          backgroundColor: AppTheme.card,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusCard)),
          title: const Row(
            children: [
              Icon(Icons.gavel_rounded, color: AppTheme.primaryGreen, size: 22),
              SizedBox(width: 8),
              Text('Resolve Issue', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Issue #${issue.id} • Donation #${issue.donationId}',
                  style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 12),
                Text(
                  context.tr('admin_notes_hint'),
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 6),
                TextField(
                  controller: notesController,
                  maxLines: 3,
                  decoration: InputDecoration(
                    hintText: context.tr('admin_notes_hint'),
                    hintStyle: const TextStyle(fontSize: 12),
                    filled: true,
                    fillColor: AppTheme.background,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.radiusInput)),
                  ),
                ),
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      context.tr('reliability_penalty_label'),
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                    Text(
                      '-${penalty.toStringAsFixed(1)} pts',
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.error),
                    ),
                  ],
                ),
                Slider(
                  value: penalty,
                  min: 0.0,
                  max: 10.0,
                  divisions: 20,
                  activeColor: AppTheme.error,
                  label: '-${penalty.toStringAsFixed(1)} pts',
                  onChanged: (val) => setModalState(() => penalty = val),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(context.tr('cancel')),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryGreen,
                foregroundColor: Colors.white,
              ),
              onPressed: isSubmitting
                  ? null
                  : () async {
                      final messenger = ScaffoldMessenger.of(context);
                      final errText = context.tr('err_server');
                      setModalState(() => isSubmitting = true);
                      final adminProv = Provider.of<AdminProvider>(context, listen: false);
                      final ok = await adminProv.resolveAdminIssue(
                        issue.id,
                        status: 'RESOLVED',
                        adminNotes: notesController.text.trim().isNotEmpty ? notesController.text.trim() : null,
                        reliabilityPenalty: penalty > 0 ? penalty : null,
                      );
                      if (ctx.mounted) Navigator.of(ctx).pop();
                      messenger.showSnackBar(
                        SnackBar(
                          content: Text(ok ? '✅ Issue resolved' : errText),
                          backgroundColor: ok ? AppTheme.primaryGreen : AppTheme.error,
                        ),
                      );
                    },
              child: Text(context.tr('confirm')),
            ),
          ],
        ),
      ),
    );
  }

  void _dismissIssue(RescueIssueReportModel issue) async {
    final adminProv = Provider.of<AdminProvider>(context, listen: false);
    final ok = await adminProv.dismissAdminIssue(issue.id);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? 'Report dismissed' : context.tr('err_server')),
          backgroundColor: ok ? AppTheme.textSecondary : AppTheme.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);
    final overview = adminProv.feedbackOverview;
    final issues = adminProv.adminIssues;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(context.tr('admin_feedback_title'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
            Text(context.tr('role_admin'), style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
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
              // ── KPI Overview Cards ────────────────────────────────────────
              if (overview != null) ...[
                Row(
                  children: [
                    Expanded(
                      child: _buildMetricCard(
                        title: context.tr('admin_avg_rating'),
                        value: '${(overview['average_rating'] as num?)?.toStringAsFixed(1) ?? "5.0"} ★',
                        subtitle: '${overview['total_feedback'] ?? 0} ${context.tr('admin_total_feedback')}',
                        color: const Color(0xFFF59E0B),
                        icon: Icons.star_rounded,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _buildMetricCard(
                        title: context.tr('admin_open_issues'),
                        value: '${overview['open_issues_count'] ?? 0}',
                        subtitle: '${overview['critical_issues_count'] ?? 0} ${context.tr('admin_critical_issues')}',
                        color: AppTheme.error,
                        icon: Icons.warning_amber_rounded,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space16),
              ],

              // ── Filters Row ───────────────────────────────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    context.tr('admin_issues_queue'),
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Severity and Status Filter Chips
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    ...['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) {
                      final isSel = _selectedSeverity == sev;
                      return Padding(
                        padding: const EdgeInsets.only(right: 6.0),
                        child: FilterChip(
                          label: Text(
                            sev == 'ALL' ? 'All Severities' : sev,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
                              color: isSel ? Colors.white : AppTheme.textPrimary,
                            ),
                          ),
                          selected: isSel,
                          selectedColor: sev == 'ALL' ? AppTheme.primaryGreen : _getSeverityColor(sev),
                          backgroundColor: AppTheme.card,
                          onSelected: (_) {
                            setState(() => _selectedSeverity = sev);
                            _loadData();
                          },
                        ),
                      );
                    }),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space12),

              // ── Issue List ────────────────────────────────────────────────
              if (adminProv.isLoading)
                LoadingStateWidget(message: context.tr('processing'))
              else if (issues.isEmpty)
                const EmptyStateWidget(
                  title: 'No Issues in Queue',
                  subtitle: 'All rescue operations and reports are currently clear.',
                  icon: Icons.check_circle_outline,
                )
              else
                ...issues.map((issue) {
                  final sevColor = _getSeverityColor(issue.severity);
                  final statColor = _getStatusColor(issue.status);

                  return Container(
                    margin: const EdgeInsets.only(bottom: AppTheme.space12),
                    padding: const EdgeInsets.all(AppTheme.space16),
                    decoration: BoxDecoration(
                      color: AppTheme.card,
                      borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                      border: Border.all(
                        color: issue.severity == 'CRITICAL' ? AppTheme.error.withValues(alpha: 0.5) : AppTheme.border,
                        width: issue.severity == 'CRITICAL' ? 1.5 : 1.0,
                      ),
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
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: sevColor.withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(4),
                                    border: Border.all(color: sevColor.withValues(alpha: 0.3)),
                                  ),
                                  child: Row(
                                    children: [
                                      if (issue.isFoodSafetyIncident) ...[
                                        const Icon(Icons.warning_rounded, size: 12, color: AppTheme.error),
                                        const SizedBox(width: 4),
                                      ],
                                      Text(
                                        issue.severity,
                                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: sevColor),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  'Donation #${issue.donationId}',
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                              ],
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: statColor.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                issue.status,
                                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: statColor),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppTheme.space12),

                        Text(
                          issue.category.replaceAll('_', ' ').toUpperCase(),
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.textPrimary),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          issue.description,
                          style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary, height: 1.3),
                        ),

                        if (issue.isFoodSafetyIncident && issue.foodSafetyDetails != null) ...[
                          const SizedBox(height: 8),
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: AppTheme.error.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: AppTheme.error.withValues(alpha: 0.2)),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(Icons.local_hospital_outlined, color: AppTheme.error, size: 16),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    'Incident Details: ${issue.foodSafetyDetails!}',
                                    style: const TextStyle(fontSize: 11, color: AppTheme.error, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],

                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Text(
                              'Reporter: ${issue.reporterRole.toUpperCase()} (History: ${issue.reporterHistoryCount})',
                              style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                            ),
                            if (issue.reportedUserName != null) ...[
                              const SizedBox(width: 8),
                              Text(
                                '• Target: ${issue.reportedUserName}',
                                style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                              ),
                            ],
                          ],
                        ),

                        if (issue.status == 'OPEN' || issue.status == 'UNDER_REVIEW' || issue.status == 'ACTION_REQUIRED') ...[
                          const Divider(height: 20),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              OutlinedButton(
                                onPressed: () => _dismissIssue(issue),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: AppTheme.textSecondary,
                                  minimumSize: const Size(0, 36),
                                ),
                                child: Text(context.tr('dismiss_issue_btn')),
                              ),
                              const SizedBox(width: 8),
                              ElevatedButton(
                                onPressed: () => _showResolveModal(context, issue),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppTheme.primaryGreen,
                                  foregroundColor: Colors.white,
                                  minimumSize: const Size(0, 36),
                                ),
                                child: Text(context.tr('resolve_issue_btn')),
                              ),
                            ],
                          ),
                        ] else if (issue.adminNotes != null) ...[
                          const Divider(height: 16),
                          Text(
                            'Admin Notes: ${issue.adminNotes!}',
                            style: const TextStyle(fontSize: 11, color: AppTheme.primaryGreen, fontStyle: FontStyle.italic),
                          ),
                        ],
                      ],
                    ),
                  );
                }),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(
        currentRole: 'admin',
        currentIndex: 0,
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
              Text(title, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, fontWeight: FontWeight.w600)),
              Icon(icon, size: 18, color: color),
            ],
          ),
          const SizedBox(height: 6),
          Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
          const SizedBox(height: 2),
          Text(subtitle, style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary)),
        ],
      ),
    );
  }
}
