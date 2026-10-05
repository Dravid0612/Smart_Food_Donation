import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../models/donation_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/availability_toggle.dart';
import '../../widgets/vehicle_capacity_card.dart';
import '../../widgets/donation_card.dart';
import '../../widgets/rescue_ring.dart';
import '../../widgets/urgency_badge.dart';
import '../../core/utils/food_rescue_status_helper.dart';
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

  Future<void> _handleAcceptRescue(int taskId) async {
    final taskProv = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final ok = await taskProv.acceptPickupRequest(taskId);
    if (!mounted) return;
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${context.tr('accept_rescue')}! 🛵'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
      _loadData();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(taskProv.errorMessage != null ? context.trError(taskProv.errorMessage!) : context.trError('err_server')),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  Future<void> _handlePassRescue(int taskId) async {
    final taskProv = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final ok = await taskProv.rejectPickupRequest(taskId);
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
    final taskProv = Provider.of<VolunteerTaskProvider>(context);
    final notifProv = Provider.of<NotificationProvider>(context);
    final user = auth.currentUser;

    final activeTasks = taskProv.assignedTasks
        .where((d) => ['volunteer_assigned', 'accepted', 'en_route', 'arrived', 'collected', 'in_transit'].contains(d.status.toLowerCase()) && (d.assignedVolunteerId == user?.id || taskProv.getAssignmentId(d.id) != null || d.status.toLowerCase() != 'accepted'))
        .toList();

    // Show ONLY tasks that are genuinely feasible (Section 5) and only when Available (Section 4)
    final isAvailableNow = taskProv.isAvailable && _currentAvailability != 'offline';
    final availablePickups = !isAvailableNow
        ? <DonationModel>[]
        : taskProv.assignedTasks.where((d) {
            if (d.status.toLowerCase() != 'accepted') return false;
            // Exclude direct NGO self-pickup from volunteer dispatch
            if (d.pickupMode == 'self_pickup') return false;
            // Exclude tasks already assigned to another volunteer
            if (d.assignedVolunteerId != null && d.assignedVolunteerId != user?.id) return false;

            final remainingMins = d.remainingMinutes ??
                FoodRescueStatusHelper.calculateRemainingMinutes(d.expiryTime);
            if (remainingMins <= 0) return false;

            if (d.feasibility != null && !d.feasibility!.isFeasible) return false;

            final fStatus = d.feasibilityStatus.toUpperCase().trim();
            if (fStatus == 'INFEASIBLE' || fStatus == 'RESCUE_UNLIKELY' || fStatus == 'WINDOW_ENDED') {
              return false;
            }

            return true;
          }).toList();

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
          IconButton(
            icon: const Icon(Icons.history_outlined),
            tooltip: context.tr('task_history'),
            onPressed: () => context.push('/volunteer/history'),
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
              // ── 1. VEHICLE PROFILE & CAPACITY CARD (V5) ───────────────────
              VehicleCapacityCard(
                vehicleType: user?.vehicleType ?? 'Bike',
                capacity: user?.carryingCapacity ?? 25,
                onEdit: () => context.push('/volunteer/vehicle'),
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
                          label: Text(
                            task.status.toLowerCase() == 'collected'
                                ? context.tr('action_deliver')
                                : context.tr('action_go_to_pickup'),
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
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

                if (!isAvailableNow)
                  Container(
                    margin: const EdgeInsets.only(bottom: AppTheme.space16),
                    padding: const EdgeInsets.all(AppTheme.space14),
                    decoration: BoxDecoration(
                      color: AppTheme.warning.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                      border: Border.all(color: AppTheme.warning.withValues(alpha: 0.4)),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.pause_circle_outline, color: AppTheme.warning, size: 22),
                        SizedBox(width: AppTheme.space12),
                        Expanded(
                          child: Text(
                            'You are currently marked as Unavailable. Toggle your status to "Available" in the app bar to receive new rescue tasks.',
                            style: TextStyle(fontSize: 13, color: AppTheme.textPrimary),
                          ),
                        ),
                      ],
                    ),
                  ),

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
                      final remainingMins = task.remainingMinutes ??
                          FoodRescueStatusHelper.calculateRemainingMinutes(task.expiryTime);
                      final urgencyInfo = FoodRescueStatusHelper.getRescueUrgency(
                        context,
                        task.urgencyLevel,
                        remainingMinutes: remainingMins,
                      );

                      return Container(
                        margin: const EdgeInsets.only(bottom: AppTheme.space16),
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
                            // Top Row: Category + Urgency Badge
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: AppTheme.primaryGreen.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                                  ),
                                  child: Text(
                                    context.trCategory(task.foodCategory).toUpperCase(),
                                    style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.primaryGreen,
                                      letterSpacing: 0.4,
                                    ),
                                  ),
                                ),
                                UrgencyBadge(
                                  level: urgencyInfo.rawKey,
                                  remainingMinutes: remainingMins,
                                ),
                              ],
                            ),
                            const SizedBox(height: AppTheme.space12),

                            // Row: Food Name, Quantity & Rescue Ring
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.center,
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        context.trFood(task.foodName),
                                        style: const TextStyle(
                                          fontSize: 17,
                                          fontWeight: FontWeight.bold,
                                          color: AppTheme.textPrimary,
                                        ),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 3),
                                      Text(
                                        '${task.quantity.toInt()} ${context.trUnit(task.quantityUnit)}',
                                        style: const TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.bold,
                                          color: AppTheme.primaryGreen,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: AppTheme.space12),
                                RescueRing.compact(
                                  remainingMinutes: remainingMins,
                                  urgencyOverride: task.urgencyLevel,
                                ),
                              ],
                            ),
                            const SizedBox(height: AppTheme.space12),

                            // Logistics Details: Pickup Area, Drop-off Area, Distance & Estimated Time
                            Container(
                              padding: const EdgeInsets.all(AppTheme.space10),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade50,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.grey.shade200),
                              ),
                              child: Column(
                                children: [
                                  Row(
                                    children: [
                                      const Icon(Icons.store_outlined, size: 15, color: AppTheme.textSecondary),
                                      const SizedBox(width: 6),
                                      Text(
                                        '${context.tr('pickup_area')}: ',
                                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                                      ),
                                      Expanded(
                                        child: Text(
                                          task.pickupAddress,
                                          style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Row(
                                    children: [
                                      const Icon(Icons.home_work_outlined, size: 15, color: AppTheme.primaryGreen),
                                      const SizedBox(width: 6),
                                      Text(
                                        '${context.tr('dropoff_area')}: ',
                                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                                      ),
                                      Expanded(
                                        child: Text(
                                          task.ngoName ?? context.tr('role_ngo'),
                                          style: const TextStyle(fontSize: 12, color: AppTheme.primaryGreen, fontWeight: FontWeight.w600),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Row(
                                    children: [
                                      const Icon(Icons.straighten, size: 15, color: AppTheme.secondaryTerracotta),
                                      const SizedBox(width: 6),
                                      Text(
                                        '${(task.currentDistanceKm ?? 3.2).toStringAsFixed(1)} km',
                                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                                      ),
                                      const SizedBox(width: 12),
                                      const Icon(Icons.timer_outlined, size: 15, color: AppTheme.secondaryTerracotta),
                                      const SizedBox(width: 6),
                                      Text(
                                        '~${(task.currentEtaMinutes ?? 20).toInt()} min ${context.tr('estimated_mission_time')}',
                                        style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: AppTheme.space16),

                            // Actions: PASS (Secondary) & ACCEPT RESCUE (Primary)
                            Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton(
                                    onPressed: () => _handlePassRescue(task.id),
                                    style: OutlinedButton.styleFrom(
                                      minimumSize: const Size(0, 44),
                                      foregroundColor: AppTheme.textSecondary,
                                      side: const BorderSide(color: AppTheme.border),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                                    ),
                                    child: Text(
                                      context.tr('pass'),
                                      style: const TextStyle(fontWeight: FontWeight.w600),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: AppTheme.space12),
                                Expanded(
                                  flex: 2,
                                  child: ElevatedButton(
                                    onPressed: () => _handleAcceptRescue(task.id),
                                    style: ElevatedButton.styleFrom(
                                      minimumSize: const Size(0, 44),
                                      backgroundColor: AppTheme.primaryGreen,
                                      foregroundColor: Colors.white,
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                                    ),
                                    child: Text(
                                      context.tr('accept_rescue'),
                                      style: const TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                ),
                              ],
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
