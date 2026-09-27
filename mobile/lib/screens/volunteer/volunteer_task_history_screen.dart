import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../widgets/availability_toggle.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/loading_state_widget.dart';

/// V6 Volunteer Task History Screen.
/// Nested screen displaying previous completed, delivered, failed, and cancelled rescue tasks.
class VolunteerTaskHistoryScreen extends StatefulWidget {
  const VolunteerTaskHistoryScreen({super.key});

  @override
  State<VolunteerTaskHistoryScreen> createState() => _VolunteerTaskHistoryScreenState();
}

class _VolunteerTaskHistoryScreenState extends State<VolunteerTaskHistoryScreen> {
  String _filter = 'All'; // All, Completed, Failed

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
    final allTasks = taskProv.assignedTasks;

    // Filter historical tasks (exclude active in-progress tasks like accepted/assigned/collected)
    final historyTasks = allTasks.where((t) {
      final s = t.status.toLowerCase();
      return ['delivered', 'completed', 'cancelled', 'failed', 'expired'].contains(s);
    }).toList();

    var filteredTasks = historyTasks;
    if (_filter == 'Completed') {
      filteredTasks = historyTasks.where((t) => ['delivered', 'completed'].contains(t.status.toLowerCase())).toList();
    } else if (_filter == 'Failed') {
      filteredTasks = historyTasks.where((t) => ['failed', 'cancelled', 'expired'].contains(t.status.toLowerCase())).toList();
    }

    final totalMeals = taskProv.totalMealsTransported;
    final totalCompleted = taskProv.completedCount;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(
          context.tr('task_history'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        actions: const [
          AvailabilityToggle(),
          SizedBox(width: 8),
        ],
      ),
      body: taskProv.isLoading && historyTasks.isEmpty
          ? LoadingStateWidget(message: context.tr('loading'))
          : RefreshIndicator(
              onRefresh: () => taskProv.fetchMyTasks(),
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(AppTheme.space16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Top Pinned Operational Impact Summary
                    Container(
                      padding: const EdgeInsets.all(AppTheme.space16),
                      decoration: BoxDecoration(
                        color: AppTheme.card,
                        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                        border: Border.all(color: AppTheme.border),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.04),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  context.tr('meals_transported_stat').toUpperCase(),
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.primaryGreen.withValues(alpha: 0.9),
                                    letterSpacing: 0.5,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '$totalMeals',
                                  style: const TextStyle(
                                    fontSize: 26,
                                    fontWeight: FontWeight.w900,
                                    color: AppTheme.primaryGreen,
                                  ),
                                ),
                                Text(
                                  context.trUnit('Meals'),
                                  style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                ),
                              ],
                            ),
                          ),
                          Container(width: 1, height: 48, color: AppTheme.border),
                          Expanded(
                            child: Padding(
                              padding: const EdgeInsets.only(left: AppTheme.space16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    context.tr('status_completed').toUpperCase(),
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.trustTeal.withValues(alpha: 0.9),
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    '$totalCompleted',
                                    style: const TextStyle(
                                      fontSize: 26,
                                      fontWeight: FontWeight.w900,
                                      color: AppTheme.trustTeal,
                                    ),
                                  ),
                                  Text(
                                    context.tr('rescues_completed_count'),
                                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppTheme.space16),

                    // Filter Chips
                    Row(
                      children: [
                        _buildFilterChip('All', context.tr('all_filter')),
                        const SizedBox(width: 8),
                        _buildFilterChip('Completed', context.tr('status_completed')),
                        const SizedBox(width: 8),
                        _buildFilterChip('Failed', context.tr('status_cancelled')),
                      ],
                    ),
                    const SizedBox(height: AppTheme.space16),

                    // Task List or Empty State
                    if (filteredTasks.isEmpty) ...[
                      EmptyStateWidget(
                        icon: Icons.history,
                        title: context.tr('no_tasks_history'),
                        subtitle: context.tr('task_history_desc'),
                      ),
                    ] else ...[
                      ...filteredTasks.map((task) {
                        final isCompleted = ['delivered', 'completed'].contains(task.status.toLowerCase());
                        final statusColor = isCompleted ? AppTheme.primaryGreen : AppTheme.criticalCrimson;

                        return Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          decoration: BoxDecoration(
                            color: AppTheme.card,
                            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                            border: Border.all(color: AppTheme.border),
                          ),
                          child: InkWell(
                            onTap: () => context.push('/volunteer/task/${task.id}'),
                            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                            child: Padding(
                              padding: const EdgeInsets.all(AppTheme.space16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          task.foodName,
                                          style: const TextStyle(
                                            fontSize: 16,
                                            fontWeight: FontWeight.bold,
                                            color: AppTheme.textPrimary,
                                          ),
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                        decoration: BoxDecoration(
                                          color: statusColor.withValues(alpha: 0.1),
                                          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                                        ),
                                        child: Text(
                                          context.trStatus(task.status),
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.bold,
                                            color: statusColor,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Row(
                                    children: [
                                      const Icon(Icons.shopping_bag_outlined, size: 14, color: AppTheme.textSecondary),
                                      const SizedBox(width: 4),
                                      Text(
                                        '${task.quantity.toInt()} ${context.trUnit(task.quantityUnit)}',
                                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                                      ),
                                      const SizedBox(width: 14),
                                      const Icon(Icons.place_outlined, size: 14, color: AppTheme.textSecondary),
                                      const SizedBox(width: 4),
                                      Expanded(
                                        child: Text(
                                          task.pickupLocation,
                                          style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(
                                        task.timeRemainingFormatted,
                                        style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                                      ),
                                      Row(
                                        children: [
                                          Text(
                                            context.tr('details'),
                                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                                          ),
                                          const Icon(Icons.chevron_right, size: 16, color: AppTheme.primaryGreen),
                                        ],
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      }),
                    ],
                    const SizedBox(height: AppTheme.space32),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildFilterChip(String key, String label) {
    final isSelected = _filter == key;
    return InkWell(
      onTap: () => setState(() => _filter = key),
      borderRadius: BorderRadius.circular(AppTheme.radiusPill),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryGreen.withValues(alpha: 0.12) : AppTheme.card,
          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
          border: Border.all(
            color: isSelected ? AppTheme.primaryGreen : AppTheme.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }
}
