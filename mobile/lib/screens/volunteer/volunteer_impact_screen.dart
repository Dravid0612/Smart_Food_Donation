import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../widgets/loading_state_widget.dart';

/// Volunteer Impact Screen showing verified meals transported and reliability metrics.
class VolunteerImpactScreen extends StatefulWidget {
  const VolunteerImpactScreen({super.key});

  @override
  State<VolunteerImpactScreen> createState() => _VolunteerImpactScreenState();
}

class _VolunteerImpactScreenState extends State<VolunteerImpactScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<VolunteerTaskProvider>(context, listen: false).fetchMyTasks();
    });
  }

  @override
  Widget build(BuildContext context) {
    final taskProv = Provider.of<VolunteerTaskProvider>(context);
    final tasks = taskProv.assignedTasks;
    final completedTasks = tasks.where((d) => ['delivered', 'completed'].contains(d.status.toLowerCase())).toList();

    final pickupsCompleted = completedTasks.length;
    final mealsTransported = completedTasks.fold<int>(0, (s, d) => s + d.quantity.toInt());
    final successRate = tasks.isEmpty ? 100 : ((pickupsCompleted / tasks.length) * 100).round();
    final co2SavedKg = (mealsTransported * 0.22).toStringAsFixed(1);

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('impact_dashboard')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: taskProv.isLoading
          ? LoadingStateWidget(message: context.tr('processing'))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(AppTheme.space16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Hero Impact Card ──────────────────────────────────────
                  Container(
                    padding: const EdgeInsets.all(AppTheme.space20),
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
                            const Icon(Icons.volunteer_activism, color: AppTheme.primaryGreen, size: 22),
                            const SizedBox(width: AppTheme.space8),
                            Text(
                              context.tr('impact_summary').toUpperCase(),
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.textSecondary,
                                letterSpacing: 0.8,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppTheme.space16),
                        _buildStatRow(context.tr('completed_donations'), '$pickupsCompleted', Icons.local_shipping_outlined),
                        _buildStatRow(context.tr('meals_rescued'), '$mealsTransported', Icons.restaurant_outlined),
                        _buildStatRow(context.tr('status_delivered'), '$successRate%', Icons.verified_outlined),
                        _buildStatRow(context.tr('co2_saved'), '$co2SavedKg kg', Icons.cloud_outlined),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppTheme.space24),

                  Container(
                    padding: const EdgeInsets.all(AppTheme.space16),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryGreen.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                      border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.25)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.shield_outlined, color: AppTheme.primaryGreen, size: 32),
                        const SizedBox(width: AppTheme.space16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                context.tr('verified_partner'),
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.primaryGreen),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppTheme.space24),
                ],
              ),
            ),
    );
  }

  Widget _buildStatRow(String label, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppTheme.space8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: AppTheme.primaryGreen),
          const SizedBox(width: AppTheme.space12),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 14, color: AppTheme.textSecondary))),
          Text(value, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
        ],
      ),
    );
  }
}
