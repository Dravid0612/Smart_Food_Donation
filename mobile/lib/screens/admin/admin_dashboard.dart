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

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadAdminData();
    });
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
    final auth = Provider.of<AuthProvider>(context);
    final adminProv = Provider.of<AdminProvider>(context);

    final stats = adminProv.statistics;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin System Portal'),
        actions: [
          IconButton(
            icon: const Icon(Icons.account_circle_outlined),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadAdminData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Admin Header Callout
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      'System Administration',
                      style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Real-time overview of platform activity, user management, and NGO verifications.',
                      style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Overview Cards Grid
              if (adminProv.isLoading || stats == null)
                const LoadingIndicatorWidget(message: 'Gathering system analytics...')
              else ...[
                GridView.count(
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.6,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  children: [
                    _buildMetricCard('Total Users', '${stats['total_users']}', Icons.people, Colors.blue),
                    _buildMetricCard('Total Donors', '${stats['total_donors']}', Icons.volunteer_activism, const Color(0xFF10B981)),
                    _buildMetricCard('Registered NGOs', '${stats['total_ngos']}', Icons.business, Colors.amber),
                    _buildMetricCard('Volunteers', '${stats['total_volunteers']}', Icons.directions_bike, Colors.purple),
                    _buildMetricCard('Total Donations', '${stats['total_donations']}', Icons.fastfood, Colors.indigo),
                    _buildMetricCard('Meals Shared', '${(stats['meals_donated'] as num).toInt()}', Icons.restaurant, Colors.teal),
                  ],
                ),
                const SizedBox(height: 24),

                // Quick Admin Navigation Buttons
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
                        label: Text('NGO Verification (${stats['unverified_ngos']})'),
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF047857)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 28),

                // FL Chart: Donation Category Analytics
                const Text('Food Category Breakdown', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
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
                      const Text('Distribution across registered food categories', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetricCard(String title, String value, IconData icon, Color color) {
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
              Expanded(child: Text(title, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)), overflow: TextOverflow.ellipsis)),
            ],
          ),
          const SizedBox(height: 6),
          Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
        ],
      ),
    );
  }
}
