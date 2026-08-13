import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../providers/donation_provider.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/status_chip.dart';
import '../../widgets/urgency_chip.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/empty_state.dart';

class VolunteerDashboardScreen extends StatefulWidget {
  const VolunteerDashboardScreen({super.key});

  @override
  State<VolunteerDashboardScreen> createState() => _VolunteerDashboardScreenState();
}

class _VolunteerDashboardScreenState extends State<VolunteerDashboardScreen> {
  bool _isAvailable = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadVolunteerData();
    });
  }

  Future<void> _loadVolunteerData() async {
    final donationProv = Provider.of<DonationProvider>(context, listen: false);
    final notifProv = Provider.of<NotificationProvider>(context, listen: false);

    await Future.wait([
      donationProv.fetchDonations(),
      notifProv.fetchNotifications(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final donationProv = Provider.of<DonationProvider>(context);
    final notifProv = Provider.of<NotificationProvider>(context);

    final user = auth.currentUser;
    final allDonations = donationProv.donations;

    final activeAssignments = allDonations.where((d) => ['accepted', 'volunteer_assigned', 'collected'].contains(d.status)).toList();
    final completedDeliveries = allDonations.where((d) => d.status == 'completed' || d.status == 'delivered').toList();

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(user?.name ?? 'Volunteer', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const Text('Volunteer Logistics Portal', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
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
                    decoration: const BoxDecoration(color: Colors.redAccent, shape: BoxShape.circle),
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
        onRefresh: _loadVolunteerData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Availability Toggle Card
              CustomCard(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        CircleAvatar(
                          backgroundColor: _isAvailable ? const Color(0xFFD1FAE5) : Colors.grey.shade200,
                          child: Icon(
                            _isAvailable ? Icons.directions_bike : Icons.directions_bike_outlined,
                            color: _isAvailable ? const Color(0xFF10B981) : Colors.grey,
                          ),
                        ),
                        const SizedBox(width: 14),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _isAvailable ? 'Status: Available for Pickups' : 'Status: Offline',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                            ),
                            Text(
                              _isAvailable ? 'Ready to receive route dispatches' : 'Turn on to accept food pickups',
                              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                            ),
                          ],
                        ),
                      ],
                    ),
                    Switch(
                      value: _isAvailable,
                      activeColor: const Color(0xFF10B981),
                      onChanged: (val) => setState(() => _isAvailable = val),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Metrics Row
              Row(
                children: [
                  Expanded(
                    child: _buildMetricTile("Today's Pickups", '${activeAssignments.length}', Icons.local_shipping, Colors.blue),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildMetricTile('Completed Deliveries', '${completedDeliveries.length}', Icons.task_alt, const Color(0xFF10B981)),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Section Header
              const Text('Assigned Pickups & Deliveries', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
              const SizedBox(height: 12),

              if (donationProv.isLoading)
                const LoadingIndicatorWidget(message: 'Syncing volunteer dispatch tasks...')
              else if (activeAssignments.isEmpty)
                EmptyStateWidget(
                  icon: Icons.directions_bike_outlined,
                  title: 'No Pending Pickups',
                  message: 'You have no assigned food pickups right now.',
                )
              else
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: activeAssignments.length,
                  itemBuilder: (context, index) {
                    final item = activeAssignments[index];
                    return CustomCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(12),
                                child: Image.network(
                                  item.imageUrl ?? 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
                                  width: 70,
                                  height: 70,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => Container(width: 70, height: 70, color: Colors.grey.shade200, child: const Icon(Icons.fastfood)),
                                ),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Expanded(
                                          child: Text(
                                            item.foodName,
                                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                        UrgencyChip(urgency: item.urgencyLevel),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      '${item.quantity.toInt()} ${item.quantityUnit} • ${item.foodCategory}',
                                      style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          const Divider(),

                          // Route details: Pickup & Destination
                          Row(
                            children: [
                              const Icon(Icons.store, size: 16, color: Colors.blue),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  'Pickup: ${item.pickupAddress}',
                                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              const Icon(Icons.location_on, size: 16, color: Color(0xFF10B981)),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  'Destination: ${item.ngoName ?? "Assigned NGO"}',
                                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),

                          // Action Buttons
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              StatusChip(status: item.status),
                              Row(
                                children: [
                                  if (item.status == 'accepted' || item.status == 'volunteer_assigned')
                                    ElevatedButton.icon(
                                      onPressed: () async {
                                        final prov = Provider.of<DonationProvider>(context, listen: false);
                                        final ok = await prov.collectDonation(item.id);
                                        if (ok && context.mounted) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            const SnackBar(content: Text('Marked as Food Collected! En route to NGO.'), backgroundColor: Colors.amber),
                                          );
                                        }
                                      },
                                      style: ElevatedButton.styleFrom(backgroundColor: Colors.amber.shade700),
                                      icon: const Icon(Icons.shopping_bag_outlined),
                                      label: const Text('Mark Collected'),
                                    )
                                  else if (item.status == 'collected')
                                    ElevatedButton.icon(
                                      onPressed: () async {
                                        final prov = Provider.of<DonationProvider>(context, listen: false);
                                        final ok = await prov.deliverDonation(item.id);
                                        if (ok && context.mounted) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            const SnackBar(content: Text('Marked as Delivered! +10 Points awarded to Donor.'), backgroundColor: Color(0xFF10B981)),
                                          );
                                        }
                                      },
                                      icon: const Icon(Icons.task_alt),
                                      label: const Text('Mark Delivered'),
                                    ),
                                ],
                              ),
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

  Widget _buildMetricTile(String label, String value, IconData icon, Color color) {
    return CustomCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
        ],
      ),
    );
  }
}
