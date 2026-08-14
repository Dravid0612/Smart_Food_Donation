import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/status_chip.dart';
import '../../widgets/urgency_chip.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/empty_state.dart';

enum VolunteerAvailability { available, busy, offline }

class VolunteerDashboardScreen extends StatefulWidget {
  const VolunteerDashboardScreen({super.key});

  @override
  State<VolunteerDashboardScreen> createState() => _VolunteerDashboardScreenState();
}

class _VolunteerDashboardScreenState extends State<VolunteerDashboardScreen> {
  VolunteerAvailability _availability = VolunteerAvailability.available;

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

  Color get _availabilityColor {
    switch (_availability) {
      case VolunteerAvailability.available: return const Color(0xFF10B981);
      case VolunteerAvailability.busy: return const Color(0xFFF59E0B);
      case VolunteerAvailability.offline: return const Color(0xFF64748B);
    }
  }

  String get _availabilityLabel {
    switch (_availability) {
      case VolunteerAvailability.available: return '🟢  Available for Pickups';
      case VolunteerAvailability.busy: return '🟠  Busy';
      case VolunteerAvailability.offline: return '⚫  Offline';
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final taskProv = Provider.of<VolunteerTaskProvider>(context);
    final notifProv = Provider.of<NotificationProvider>(context);
    final user = auth.currentUser;

    final activeTasks = taskProv.assignedTasks
        .where((d) => ['volunteer_assigned', 'collected'].contains(d.status))
        .toList();
    final completedTasks = taskProv.assignedTasks
        .where((d) => ['delivered', 'completed'].contains(d.status))
        .toList();

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(user?.name ?? 'Volunteer', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const Text('Volunteer Portal', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
          ],
        ),
        actions: [
          Stack(alignment: Alignment.center, children: [
            IconButton(
              icon: const Icon(Icons.notifications_outlined),
              onPressed: () => context.push('/notifications'),
            ),
            if (notifProv.unreadCount > 0)
              Positioned(
                right: 8, top: 8,
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: const BoxDecoration(color: Colors.redAccent, shape: BoxShape.circle),
                  child: Text('${notifProv.unreadCount}',
                      style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ),
          ]),
          IconButton(icon: const Icon(Icons.account_circle_outlined), onPressed: () => context.push('/profile')),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── 3-State Availability Selector ────────────────────────────
              CustomCard(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        CircleAvatar(
                          backgroundColor: _availabilityColor.withOpacity(0.15),
                          child: Icon(Icons.directions_bike, color: _availabilityColor),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Availability', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                              Text(_availabilityLabel, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: VolunteerAvailability.values.map((status) {
                        final labels = {
                          VolunteerAvailability.available: '🟢 Available',
                          VolunteerAvailability.busy: '🟠 Busy',
                          VolunteerAvailability.offline: '⚫ Offline',
                        };
                        final isSelected = _availability == status;
                        return Expanded(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 3),
                            child: ChoiceChip(
                              label: Text(labels[status]!, style: TextStyle(fontSize: 11, fontWeight: isSelected ? FontWeight.bold : FontWeight.normal)),
                              selected: isSelected,
                              onSelected: (_) {
                                setState(() => _availability = status);
                                Provider.of<VolunteerTaskProvider>(context, listen: false)
                                    .setAvailability(status == VolunteerAvailability.available);
                              },
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // ── Metrics Row ──────────────────────────────────────────────
              Row(
                children: [
                  Expanded(child: _metricTile('Active Tasks', '${activeTasks.length}', Icons.local_shipping, Colors.blue)),
                  const SizedBox(width: 12),
                  Expanded(child: _metricTile('Completed', '${completedTasks.length}', Icons.task_alt, const Color(0xFF10B981))),
                  const SizedBox(width: 12),
                  Expanded(child: _metricTile('Meals Moved', '${taskProv.totalMealsTransported}', Icons.restaurant, Colors.purple)),
                ],
              ),
              const SizedBox(height: 20),

              // ── Impact Link ──────────────────────────────────────────────
              GestureDetector(
                onTap: () => context.push('/volunteer/impact'),
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFF047857), Color(0xFF10B981)]),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.emoji_events, color: Colors.amber),
                      SizedBox(width: 10),
                      Expanded(child: Text('View My Impact & Badges →', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold))),
                      Icon(Icons.chevron_right, color: Colors.white70),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // ── Active Tasks ─────────────────────────────────────────────
              const Text('My Active Pickups', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),

              if (taskProv.isLoading)
                const LoadingIndicatorWidget(message: 'Syncing your tasks...')
              else if (activeTasks.isEmpty)
                EmptyStateWidget(
                  icon: Icons.directions_bike_outlined,
                  title: _availability == VolunteerAvailability.offline
                      ? 'You\'re Offline'
                      : 'No Active Pickups',
                  message: _availability == VolunteerAvailability.offline
                      ? 'Switch to Available to receive pickup requests.'
                      : 'No assigned food pickups right now. Stay ready!',
                )
              else
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: activeTasks.length,
                  itemBuilder: (ctx, i) {
                    final item = activeTasks[i];
                    return CustomCard(
                      onTap: () => context.push('/volunteer/task/${item.id}'),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(10),
                                child: Image.network(
                                  item.imageUrl ?? 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
                                  width: 60, height: 60, fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => Container(
                                    width: 60, height: 60, color: Colors.grey.shade200,
                                    child: const Icon(Icons.fastfood),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(item.foodName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15), overflow: TextOverflow.ellipsis),
                                    Text('${item.quantity.toInt()} ${item.quantityUnit} • ${item.foodCategory}',
                                        style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                                    const SizedBox(height: 4),
                                    Row(children: [StatusChip(status: item.status), const SizedBox(width: 8), UrgencyChip(urgency: item.urgencyLevel)]),
                                  ],
                                ),
                              ),
                              const Icon(Icons.chevron_right, color: Colors.grey),
                            ],
                          ),
                          const SizedBox(height: 10),
                          const Divider(),
                          Row(
                            children: [
                              const Icon(Icons.store, size: 14, color: Colors.blue),
                              const SizedBox(width: 4),
                              Expanded(child: Text('Pickup: ${item.pickupAddress}', style: const TextStyle(fontSize: 11), overflow: TextOverflow.ellipsis)),
                            ],
                          ),
                          const SizedBox(height: 3),
                          Row(
                            children: [
                              const Icon(Icons.location_on, size: 14, color: Color(0xFF10B981)),
                              const SizedBox(width: 4),
                              Expanded(child: Text('NGO: ${item.ngoName ?? "Assigned NGO"}', style: const TextStyle(fontSize: 11), overflow: TextOverflow.ellipsis)),
                            ],
                          ),
                        ],
                      ),
                    );
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _metricTile(String label, String value, IconData icon, Color color) {
    return CustomCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 6),
          Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          Text(label, style: const TextStyle(fontSize: 10, color: Color(0xFF64748B))),
        ],
      ),
    );
  }
}
