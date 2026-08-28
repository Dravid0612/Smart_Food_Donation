import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/availability_toggle.dart';
import '../../widgets/vehicle_capacity_card.dart';
import '../../widgets/donation_card.dart';
import '../../widgets/skeleton_loader.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';

/// Volunteer Courier Home Screen prioritizing the single dominant active task.
class VolunteerDashboardScreen extends StatefulWidget {
  const VolunteerDashboardScreen({super.key});

  @override
  State<VolunteerDashboardScreen> createState() => _VolunteerDashboardScreenState();
}

class _VolunteerDashboardScreenState extends State<VolunteerDashboardScreen> {
  String _currentAvailability = 'available';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
  }

  Future<void> _loadData() async {
    final taskProv = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final notifProv = Provider.of<NotificationProvider>(context, listen: false);
    await Future.wait([taskProv.fetchMyTasks(), notifProv.fetchNotifications()]);
  }

  void _onStatusChanged(String newStatus) {
    setState(() => _currentAvailability = newStatus);
    Provider.of<VolunteerTaskProvider>(context, listen: false)
        .setAvailability(newStatus == 'available');
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final taskProv = Provider.of<VolunteerTaskProvider>(context);
    final notifProv = Provider.of<NotificationProvider>(context);
    final user = auth.currentUser;

    final activeTasks = taskProv.assignedTasks
        .where((d) => ['volunteer_assigned', 'collected'].contains(d.status.toLowerCase()))
        .toList();
    final availablePickups = taskProv.assignedTasks
        .where((d) => d.status.toLowerCase() == 'accepted')
        .toList();
    final completedTasks = taskProv.assignedTasks
        .where((d) => ['delivered', 'completed'].contains(d.status.toLowerCase()))
        .toList();

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(user?.name ?? context.tr('role_volunteer'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text(context.tr('verified_partner'), style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
          ],
        ),
        actions: [
          AvailabilityToggle(
            currentStatus: _currentAvailability,
            onStatusChanged: _onStatusChanged,
          ),
          const SizedBox(width: AppTheme.space8),
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
                    child: Text('${notifProv.unreadCount}',
                        style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                  ),
                ),
            ],
          ),
          IconButton(icon: const Icon(Icons.account_circle_outlined), onPressed: () => context.push('/profile')),
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
              // ── 1. VEHICLE PROFILE & CAPACITY CARD ────────────────────────
              VehicleCapacityCard(
                vehicleType: user?.vehicleType ?? 'Bike',
                capacity: user?.carryingCapacity ?? 50,
              ),
              const SizedBox(height: AppTheme.space16),

              // ── 2. ACTIVE TASK SECTION (DOMINATES SCREEN IF ACTIVE) ───────
              if (activeTasks.isNotEmpty) ...[
                Row(
                  children: [
                    const Icon(Icons.bolt, color: AppTheme.secondaryTerracotta, size: 20),
                    const SizedBox(width: 6),
                    Text(
                      context.tr('active_rescues').toUpperCase(),
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textPrimary,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space12),

                ...activeTasks.map((task) => Container(
                  margin: const EdgeInsets.only(bottom: AppTheme.space16),
                  padding: const EdgeInsets.all(AppTheme.space16),
                  decoration: BoxDecoration(
                    color: AppTheme.card,
                    borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                    border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.4), width: 1.5),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primaryGreen.withValues(alpha: 0.06),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          Expanded(
                            child: Text(
                              context.trFood(task.foodName),
                              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '${task.quantity.toInt()} ${context.trUnit(task.quantityUnit)}',
                            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppTheme.space12),
                      Row(
                        children: [
                          const Icon(Icons.store_mall_directory_outlined, size: 16, color: AppTheme.textSecondary),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              task.pickupAddress,
                              style: const TextStyle(fontSize: 13, color: AppTheme.textPrimary),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          const Icon(Icons.home_work_outlined, size: 16, color: AppTheme.primaryGreen),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              task.ngoName ?? context.tr('role_ngo'),
                              style: const TextStyle(fontSize: 13, color: AppTheme.primaryGreen, fontWeight: FontWeight.w600),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppTheme.space16),
                      SizedBox(
                        width: double.infinity,
                        height: 48,
                        child: ElevatedButton.icon(
                          onPressed: () => context.push('/volunteer/task/${task.id}'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryGreen,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                          ),
                          icon: const Icon(Icons.navigation_outlined, size: 18),
                          label: Text(context.tr('rescue_live_tracking'), style: const TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                )),
              ] else ...[
                // ── 3. NO ACTIVE TASK: SHOW RECENT / AVAILABLE TASKS ─────────
                Text(
                  context.tr('active_rescues'),
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: AppTheme.space12),

                if (taskProv.isLoading && taskProv.assignedTasks.isEmpty)
                  const Column(
                    children: [
                      TaskCardSkeleton(),
                      TaskCardSkeleton(),
                    ],
                  )
                else if (availablePickups.isEmpty && completedTasks.isEmpty)
                  EmptyStateWidget(
                    icon: Icons.directions_bike_outlined,
                    title: context.tr('no_active_deliveries'),
                    description: context.tr('no_donations_desc'),
                  )
                else ...[
                  if (availablePickups.isNotEmpty) ...[
                    ...availablePickups.map((task) {
                      final fitsCapacity = task.quantity <= (user?.carryingCapacity ?? 50);
                      return Container(
                        margin: const EdgeInsets.only(bottom: AppTheme.space12),
                        padding: const EdgeInsets.all(AppTheme.space16),
                        decoration: BoxDecoration(
                          color: AppTheme.card,
                          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                          border: Border.all(
                            color: fitsCapacity ? AppTheme.primaryGreen.withValues(alpha: 0.3) : AppTheme.error.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Text(
                                    context.trFood(task.foodName),
                                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: fitsCapacity ? AppTheme.primaryGreen.withValues(alpha: 0.1) : AppTheme.error.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text(
                                    '${task.quantity.toInt()} ${context.trUnit(task.quantityUnit)}',
                                    style: TextStyle(
                                      color: fitsCapacity ? AppTheme.primaryGreen : AppTheme.error,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 13,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(task.pickupAddress, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary), maxLines: 1, overflow: TextOverflow.ellipsis),
                            Text(task.ngoName ?? context.tr('role_ngo'), style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary), maxLines: 1, overflow: TextOverflow.ellipsis),
                            const SizedBox(height: AppTheme.space12),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton(
                                onPressed: () => context.push('/volunteer/request/${task.id}'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: fitsCapacity ? AppTheme.primaryGreen : Colors.grey.shade700,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(vertical: 10),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                                ),
                                child: Text(context.tr('accept_pickup'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                              ),
                            ),
                          ],
                        ),
                      );
                    }),
                    const SizedBox(height: AppTheme.space16),
                  ],

                  if (completedTasks.isNotEmpty) ...[
                    Text(context.tr('status_completed'), style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
                    const SizedBox(height: AppTheme.space8),
                    ...completedTasks.map((task) => DonationCard(
                      foodName: task.foodName,
                      category: task.foodCategory,
                      quantity: task.quantity,
                      quantityUnit: task.quantityUnit,
                      status: task.status,
                      locationText: task.ngoName ?? context.tr('role_ngo'),
                    )),
                  ],
                ],
              ],
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(currentRole: 'volunteer', currentIndex: 0),
    );
  }
}
