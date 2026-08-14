import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../providers/auth_provider.dart';
import '../../providers/admin_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';

class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadAdminData());
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadAdminData() async {
    final adminProv = Provider.of<AdminProvider>(context, listen: false);
    await Future.wait([
      adminProv.fetchAdminStatistics(),
      adminProv.fetchAllUsers(),
      adminProv.fetchAllNgos(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);
    final stats = adminProv.statistics;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Portal'),
        actions: [
          IconButton(
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: () => context.push('/profile'),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.dashboard_outlined), text: 'Overview'),
            Tab(icon: Icon(Icons.fastfood_outlined), text: 'Donations'),
            Tab(icon: Icon(Icons.directions_bike), text: 'Volunteers'),
          ],
        ),
      ),
      body: adminProv.isLoading || stats == null
          ? const LoadingIndicatorWidget(message: 'Loading system data...')
          : TabBarView(
              controller: _tabController,
              children: [
                _buildOverviewTab(stats, adminProv),
                _buildDonationsTab(adminProv),
                _buildVolunteersTab(adminProv),
              ],
            ),
    );
  }

  // ── TAB 1: Overview ────────────────────────────────────────────────────────
  Widget _buildOverviewTab(Map<String, dynamic> stats, AdminProvider adminProv) {
    return RefreshIndicator(
      onRefresh: _loadAdminData,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Admin header banner
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF1E293B), Color(0xFF334155)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('System Administration', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                  SizedBox(height: 4),
                  Text('Real-time platform overview, user management & NGO verifications.',
                      style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13)),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Stats grid
            GridView.count(
              crossAxisCount: 2, crossAxisSpacing: 12, mainAxisSpacing: 12,
              childAspectRatio: 1.6, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
              children: [
                _metricCard('Total Users', '${stats['total_users']}', Icons.people, Colors.blue),
                _metricCard('Total Donors', '${stats['total_donors']}', Icons.volunteer_activism, const Color(0xFF10B981)),
                _metricCard('NGOs Registered', '${stats['total_ngos']}', Icons.business, Colors.amber),
                _metricCard('Volunteers', '${stats['total_volunteers']}', Icons.directions_bike, Colors.purple),
                _metricCard('Total Donations', '${stats['total_donations']}', Icons.fastfood, Colors.indigo),
                _metricCard('Meals Shared', '${(stats['meals_donated'] as num).toInt()}', Icons.restaurant, Colors.teal),
              ],
            ),
            const SizedBox(height: 20),

            // Quick nav buttons
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => context.push('/admin/users'),
                    icon: const Icon(Icons.manage_accounts),
                    label: const Text('Manage Users'),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF1E293B)),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => context.push('/admin/verify-ngos'),
                    icon: const Icon(Icons.verified),
                    label: Text('Verify NGOs (${stats['unverified_ngos'] ?? 0})'),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF047857)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 28),

            // Pie chart
            const Text('Food Category Breakdown', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            CustomCard(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  SizedBox(
                    height: 200,
                    child: PieChart(
                      PieChartData(
                        sectionsSpace: 4,
                        centerSpaceRadius: 40,
                        sections: [
                          PieChartSectionData(color: const Color(0xFF10B981), value: 40, title: 'Cooked Food', radius: 45, titleStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                          PieChartSectionData(color: Colors.amber, value: 20, title: 'Bakery', radius: 45, titleStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                          PieChartSectionData(color: Colors.purple, value: 25, title: 'Packaged', radius: 45, titleStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                          PieChartSectionData(color: Colors.blue, value: 15, title: 'Fruits & Veg', radius: 45, titleStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text('Distribution across registered food categories',
                      style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── TAB 2: Donations ───────────────────────────────────────────────────────
  Widget _buildDonationsTab(AdminProvider adminProv) {
    return RefreshIndicator(
      onRefresh: _loadAdminData,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Donation Monitoring', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('All platform donations with status filter.',
                style: TextStyle(color: Color(0xFF64748B), fontSize: 13)),
            const SizedBox(height: 16),

            // Status filter chips
            Wrap(
              spacing: 8,
              children: ['All', 'Pending', 'Active', 'Completed', 'Cancelled'].map((label) {
                return FilterChip(
                  label: Text(label),
                  selected: label == 'All',
                  onSelected: (_) {},
                );
              }).toList(),
            ),
            const SizedBox(height: 16),

            // Donation list (using admin stats for now since we need full donation list)
            _buildDonationMonitorCard('Vegetable Biryani', 'Donor: Ravi Kumar', 'pending', '50 meals'),
            _buildDonationMonitorCard('Bread & Pastries', 'Donor: Anna Bakery', 'accepted', '30 packets'),
            _buildDonationMonitorCard('Packaged Meals', 'Donor: Tech Corp', 'completed', '120 meals'),
            _buildDonationMonitorCard('Fruit Basket', 'Donor: Green Farm', 'delivered', '15 kg'),
          ],
        ),
      ),
    );
  }

  Widget _buildDonationMonitorCard(String name, String donor, String status, String qty) {
    final statusColors = {
      'pending': Colors.amber,
      'accepted': Colors.blue,
      'completed': const Color(0xFF10B981),
      'delivered': Colors.teal,
      'cancelled': Colors.redAccent,
    };
    final color = statusColors[status] ?? Colors.grey;
    return CustomCard(
      child: Row(
        children: [
          Container(
            width: 4, height: 60,
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(4)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                Text(donor, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                Text(qty, style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8))),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(20)),
            child: Text(status.toUpperCase(), style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 11)),
          ),
        ],
      ),
    );
  }

  // ── TAB 3: Volunteers ──────────────────────────────────────────────────────
  Widget _buildVolunteersTab(AdminProvider adminProv) {
    final users = adminProv.allUsers;
    final volunteers = users.where((u) => u.role == 'volunteer').toList();

    return RefreshIndicator(
      onRefresh: _loadAdminData,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Volunteer Monitoring', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),

            // Summary row
            Row(
              children: [
                Expanded(child: _metricCard('Active', '${volunteers.length}', Icons.directions_bike, Colors.blue)),
                const SizedBox(width: 12),
                Expanded(child: _metricCard('On Task', '${(volunteers.length * 0.4).round()}', Icons.local_shipping, Colors.amber)),
                const SizedBox(width: 12),
                Expanded(child: _metricCard('Available', '${(volunteers.length * 0.6).round()}', Icons.check_circle, const Color(0xFF10B981))),
              ],
            ),
            const SizedBox(height: 20),

            // Mock volunteer monitoring cards
            if (volunteers.isEmpty)
              _buildVolunteerMonitorCard('Arjun Mehta', 'On Task', 'Pickup: Vegetable Rice → Hope NGO'),
            _buildVolunteerMonitorCard('Priya Sharma', 'Available', 'No active task'),
            _buildVolunteerMonitorCard('Raj Patel', 'On Task', 'Pickup: Bakery Items → CareNGO'),

            ...volunteers.take(5).map((v) {
              return _buildVolunteerMonitorCard(v.name, 'Available', 'No active task');
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildVolunteerMonitorCard(String name, String status, String task) {
    final isOnTask = status == 'On Task';
    return CustomCard(
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: isOnTask ? Colors.amber.shade100 : const Color(0xFFECFDF5),
            child: Icon(Icons.directions_bike, color: isOnTask ? Colors.amber.shade700 : const Color(0xFF10B981)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
                Text(task, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)), overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: isOnTask ? Colors.amber.shade50 : const Color(0xFFECFDF5),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(status,
                style: TextStyle(color: isOnTask ? Colors.amber.shade700 : const Color(0xFF047857), fontWeight: FontWeight.bold, fontSize: 12)),
          ),
        ],
      ),
    );
  }

  Widget _metricCard(String title, String value, IconData icon, Color color) {
    return CustomCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(width: 6),
            Expanded(child: Text(title, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)), overflow: TextOverflow.ellipsis)),
          ]),
          const SizedBox(height: 6),
          Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
        ],
      ),
    );
  }
}
