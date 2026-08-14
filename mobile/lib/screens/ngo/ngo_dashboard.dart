import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../providers/donation_provider.dart';
import '../../providers/ngo_provider.dart';
import '../../providers/notification_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/status_chip.dart';
import '../../widgets/urgency_chip.dart';
import '../../widgets/loading_indicator.dart';
import '../../widgets/empty_state.dart';

class NgoDashboardScreen extends StatefulWidget {
  const NgoDashboardScreen({super.key});

  @override
  State<NgoDashboardScreen> createState() => _NgoDashboardScreenState();
}

class _NgoDashboardScreenState extends State<NgoDashboardScreen> {
  int _selectedTab = 0; // 0: Available, 1: Active Pickups, 2: Completed

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadNgoData();
    });
  }

  Future<void> _loadNgoData() async {
    final donationProv = Provider.of<DonationProvider>(context, listen: false);
    final ngoProv = Provider.of<NgoProvider>(context, listen: false);
    final notifProv = Provider.of<NotificationProvider>(context, listen: false);

    await Future.wait([
      donationProv.fetchDonations(),
      ngoProv.fetchNgos(),
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

    final availableDonations = allDonations.where((d) => d.status == 'pending').toList();
    final activePickups = allDonations.where((d) => ['accepted', 'volunteer_assigned', 'collected'].contains(d.status)).toList();
    final completedDonations = allDonations.where((d) => d.status == 'completed' || d.status == 'delivered').toList();

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(user?.name ?? 'NGO Organization', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const Text('NGO Partner Portal', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
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
        onRefresh: _loadNgoData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Capacity Overview
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFECFDF5),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFA7F3D0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('NGO Capacity', style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF065F46))),
                        TextButton.icon(
                          onPressed: () => context.push('/ngo/requirements'),
                          icon: const Icon(Icons.tune, size: 16),
                          label: const Text('Food Requirements'),
                          style: TextButton.styleFrom(foregroundColor: const Color(0xFF047857)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: availableDonations.length > 0 ? 0.65 : 0.0,
                        backgroundColor: Colors.grey.shade200,
                        valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF10B981)),
                        minHeight: 10,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text('Capacity: 65% utilized • 35% available for new donations',
                        style: TextStyle(fontSize: 11, color: Color(0xFF047857))),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Metrics Summary Grid
              GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 1.6,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  _buildMetricTile('Available Nearby', '${availableDonations.length}', Icons.food_bank, const Color(0xFF10B981)),
                  _buildMetricTile('Active Pickups', '${activePickups.length}', Icons.local_shipping, Colors.blue),
                  _buildMetricTile('Completed', '${completedDonations.length}', Icons.check_circle, Colors.amber),
                  _buildMetricTile('Distributed Meals', '${completedDonations.fold<double>(0, (s, i) => s + i.quantity).toInt()}', Icons.restaurant, Colors.purple),
                ],
              ),
              const SizedBox(height: 20),

              // Segmented Tab Filter
              SegmentedButton<int>(
                segments: [
                  ButtonSegment(value: 0, label: Text('Available (${availableDonations.length})'), icon: const Icon(Icons.fastfood)),
                  ButtonSegment(value: 1, label: Text('Active (${activePickups.length})'), icon: const Icon(Icons.local_shipping)),
                  ButtonSegment(value: 2, label: Text('Completed (${completedDonations.length})'), icon: const Icon(Icons.done_all)),
                ],
                selected: {_selectedTab},
                onSelectionChanged: (val) => setState(() => _selectedTab = val.first),
              ),
              const SizedBox(height: 16),

              // Content based on selected tab
              if (donationProv.isLoading)
                const LoadingIndicatorWidget(message: 'Updating available donations feed...')
              else
                _buildDonationsList(
                  _selectedTab == 0
                      ? availableDonations
                      : _selectedTab == 1
                          ? activePickups
                          : completedDonations,
                  isAvailableTab: _selectedTab == 0,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDonationsList(List donations, {required bool isAvailableTab}) {
    if (donations.isEmpty) {
      return EmptyStateWidget(
        icon: Icons.inbox,
        title: 'No Donations Found',
        message: isAvailableTab
            ? 'There are no pending donations near your location right now.'
            : 'No donations in this category.',
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: donations.length,
      itemBuilder: (context, index) {
        final item = donations[index];
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
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Icon(Icons.location_on, size: 14, color: Colors.redAccent),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                item.pickupAddress,
                                style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              // Smart Recommendation Badge
              if (isAvailableTab) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.08),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFF10B981).withOpacity(0.2)),
                  ),
                  child: Row(
                    children: const [
                      Icon(Icons.auto_awesome, size: 14, color: Color(0xFF10B981)),
                      SizedBox(width: 6),
                      Text(
                        'Smart Match: Recommended for your NGO capacity & location',
                        style: TextStyle(fontSize: 11, color: Color(0xFF047857), fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ],

              const SizedBox(height: 12),
              const Divider(),

              // Action Buttons
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  StatusChip(status: item.status),
                  Row(
                    children: [
                      if (isAvailableTab) ...[
                        OutlinedButton(
                          onPressed: () async {
                            final prov = Provider.of<DonationProvider>(context, listen: false);
                            await prov.rejectDonation(item.id);
                          },
                          style: OutlinedButton.styleFrom(foregroundColor: Colors.redAccent),
                          child: const Text('Reject'),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton(
                          onPressed: () async {
                            final prov = Provider.of<DonationProvider>(context, listen: false);
                            final ok = await prov.acceptDonation(item.id);
                            if (ok && context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Donation Accepted! Volunteer search initiated.'), backgroundColor: Color(0xFF10B981)),
                              );
                            }
                          },
                          child: const Text('Accept Food'),
                        ),
                      ] else if (item.status == 'collected') ...[
                        ElevatedButton.icon(
                          onPressed: () => context.push('/ngo/receiving/${item.id}'),
                          icon: const Icon(Icons.task_alt),
                          label: const Text('Confirm Receipt'),
                          style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
                        ),
                      ] else ...[
                        TextButton.icon(
                          onPressed: () => context.push('/donor/detail/${item.id}'),
                          icon: const Icon(Icons.visibility),
                          label: const Text('View Timeline'),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildMetricTile(String label, String value, IconData icon, Color color) {
    return CustomCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 6),
              Expanded(child: Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)), overflow: TextOverflow.ellipsis)),
            ],
          ),
          const SizedBox(height: 6),
          Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
        ],
      ),
    );
  }
}
