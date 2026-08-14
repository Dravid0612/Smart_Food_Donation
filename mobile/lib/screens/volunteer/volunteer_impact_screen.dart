import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';

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

  // Badge definition
  final List<Map<String, dynamic>> _badges = [
    {'icon': '🚀', 'title': 'First Pickup', 'desc': 'Complete your first delivery', 'threshold': 1, 'field': 'pickups'},
    {'icon': '🚴', 'title': '50 Pickups', 'desc': 'Complete 50 pickups', 'threshold': 50, 'field': 'pickups'},
    {'icon': '🍱', 'title': '500 Meals', 'desc': 'Transport 500 meals', 'threshold': 500, 'field': 'meals'},
    {'icon': '🍱', 'title': '1,000 Meals', 'desc': 'Transport 1,000 meals', 'threshold': 1000, 'field': 'meals'},
    {'icon': '⭐', 'title': 'Reliable Volunteer', 'desc': 'Maintain 90% success rate', 'threshold': 90, 'field': 'rate'},
    {'icon': '🥇', 'title': 'Top Volunteer', 'desc': 'Complete 100 deliveries', 'threshold': 100, 'field': 'pickups'},
    {'icon': '🏥', 'title': 'NGO Partner', 'desc': 'Support 5 different NGOs', 'threshold': 5, 'field': 'ngos'},
    {'icon': '🌍', 'title': 'Community Hero', 'desc': 'Transport 2,000 meals total', 'threshold': 2000, 'field': 'meals'},
  ];

  @override
  Widget build(BuildContext context) {
    final taskProv = Provider.of<VolunteerTaskProvider>(context);
    final tasks = taskProv.assignedTasks;
    final completedTasks = tasks.where((d) => d.status == 'delivered' || d.status == 'completed').toList();

    final pickupsCompleted = completedTasks.length;
    final mealsTransported = completedTasks.fold<int>(0, (s, d) => s + d.quantity.toInt());
    final successRate = tasks.isEmpty ? 0 : ((pickupsCompleted / tasks.length) * 100).round();
    final ngosSupported = completedTasks.map((d) => d.assignedNgoId).toSet().length;
    // Simulated distance (100m avg per completed task)
    final distanceTravelled = (pickupsCompleted * 4.2).toStringAsFixed(1);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Impact'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: taskProv.isLoading
          ? const LoadingIndicatorWidget(message: 'Loading impact stats...')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Hero Stats Card ────────────────────────────────────
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF1E293B), Color(0xFF334155)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.emoji_events, color: Colors.amber, size: 28),
                            SizedBox(width: 8),
                            Text('MY IMPACT', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 2)),
                          ],
                        ),
                        const SizedBox(height: 20),
                        _statRow('Pickups Completed', '$pickupsCompleted', Icons.local_shipping),
                        _statRow('Meals Transported', '$mealsTransported', Icons.restaurant),
                        _statRow('NGOs Supported', '$ngosSupported', Icons.business),
                        _statRow('Distance Travelled', '$distanceTravelled km', Icons.map_outlined),
                        _statRow('Success Rate', '$successRate%', Icons.verified_outlined),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // ── Badges ─────────────────────────────────────────────
                  const Text('Badges & Achievements', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Text('Unlock badges by completing deliveries and milestones.',
                      style: TextStyle(color: Color(0xFF64748B), fontSize: 13)),
                  const SizedBox(height: 16),

                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 1.3,
                    ),
                    itemCount: _badges.length,
                    itemBuilder: (ctx, i) {
                      final b = _badges[i];
                      final field = b['field'] as String;
                      final threshold = b['threshold'] as int;
                      final current = field == 'pickups'
                          ? pickupsCompleted
                          : field == 'meals'
                              ? mealsTransported
                              : field == 'ngos'
                                  ? ngosSupported
                                  : successRate;
                      final unlocked = current >= threshold;

                      return AnimatedOpacity(
                        opacity: unlocked ? 1.0 : 0.45,
                        duration: const Duration(milliseconds: 300),
                        child: Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: unlocked ? const Color(0xFFFFFBEB) : const Color(0xFFF8FAFC),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: unlocked ? Colors.amber.shade300 : Colors.grey.shade200,
                              width: unlocked ? 2 : 1,
                            ),
                          ),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(b['icon'] as String, style: const TextStyle(fontSize: 30)),
                              const SizedBox(height: 6),
                              Text(b['title'] as String,
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                    color: unlocked ? const Color(0xFF92400E) : const Color(0xFF64748B),
                                  ),
                                  textAlign: TextAlign.center),
                              if (!unlocked) ...[
                                const SizedBox(height: 4),
                                Text('$current/$threshold',
                                    style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8))),
                              ] else
                                const SizedBox(height: 4),
                              if (unlocked)
                                const Icon(Icons.check_circle, color: Colors.amber, size: 16),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 24),

                  // ── Environmental Impact ───────────────────────────────
                  const Text('Environmental Impact', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _envTile(
                          icon: Icons.eco,
                          color: const Color(0xFF10B981),
                          value: '${(mealsTransported * 0.5).toStringAsFixed(1)} kg',
                          label: 'Food Waste Prevented',
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _envTile(
                          icon: Icons.co2,
                          color: Colors.blue,
                          value: '${(mealsTransported * 0.2).toStringAsFixed(1)} kg',
                          label: 'CO₂ Saved',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
    );
  }

  Widget _statRow(String label, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF94A3B8), size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(label, style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 14))),
          Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
        ],
      ),
    );
  }

  Widget _envTile({required IconData icon, required Color color, required String value, required String label}) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
          Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
        ],
      ),
    );
  }
}
