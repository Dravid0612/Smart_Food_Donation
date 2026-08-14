import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/reward_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';

class DonorRewardsScreen extends StatefulWidget {
  const DonorRewardsScreen({super.key});

  @override
  State<DonorRewardsScreen> createState() => _DonorRewardsScreenState();
}

class _DonorRewardsScreenState extends State<DonorRewardsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<RewardProvider>(context, listen: false).fetchRewardDetails();
    });
  }

  @override
  Widget build(BuildContext context) {
    final rewardProv = Provider.of<RewardProvider>(context);
    final reward = rewardProv.reward;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Community Rewards'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: rewardProv.isLoading || reward == null
          ? const LoadingIndicatorWidget(message: 'Loading your reward points...')
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                children: [
                  // Big Badge Card
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFFF59E0B), Color(0xFFD97706)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Column(
                      children: [
                        const Icon(Icons.emoji_events, size: 64, color: Colors.white),
                        const SizedBox(height: 12),
                        Text(
                          '${reward.points} Points',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.25),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            '${reward.level} Level Donor',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                        ),
                        const SizedBox(height: 20),
                        Text(
                          '${reward.pointsToNextLevel} points until next level upgrade!',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // How to Earn Points
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text('How Rewards Work', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(height: 12),

                  CustomCard(
                    child: ListTile(
                      leading: const CircleAvatar(
                        backgroundColor: Color(0xFFD1FAE5),
                        child: Icon(Icons.add_task, color: Color(0xFF10B981)),
                      ),
                      title: const Text('Complete Food Donation', style: TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: const Text('Earn +10 reward points for every successfully delivered donation.'),
                    ),
                  ),
                  const SizedBox(height: 8),

                  CustomCard(
                    child: ListTile(
                      leading: const CircleAvatar(
                        backgroundColor: Color(0xFFFEF3C7),
                        child: Icon(Icons.star, color: Colors.amber),
                      ),
                      title: const Text('Unlock Tier Badges', style: TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: const Text('Progress from Bronze -> Silver -> Gold -> Platinum levels.'),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Environmental Impact Metrics
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text('Your Environmental Impact 🌿', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(height: 12),

                  Row(
                    children: [
                      Expanded(
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: const Color(0xFFECFDF5),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: const Color(0xFFA7F3D0)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.co2, color: Color(0xFF059669), size: 28),
                              const SizedBox(height: 8),
                              Text(
                                '${(reward.points * 2.5).toStringAsFixed(1)} kg',
                                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF065F46)),
                              ),
                              const Text('CO₂ Prevented', style: TextStyle(fontSize: 12, color: Color(0xFF047857))),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEFF6FF),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: const Color(0xFFBFDBFE)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.water_drop, color: Color(0xFF2563EB), size: 28),
                              const SizedBox(height: 8),
                              Text(
                                '${(reward.points * 1000).toStringAsFixed(0)} L',
                                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF1E40AF)),
                              ),
                              const Text('Water Preserved', style: TextStyle(fontSize: 12, color: Color(0xFF1D4ED8))),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
    );
  }
}

