import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../providers/reward_provider.dart';
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
        title: Text(context.tr('impact_dashboard')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: rewardProv.isLoading || reward == null
          ? LoadingIndicatorWidget(message: context.tr('processing'))
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
                          '${reward.points} ${context.tr('meals_rescued')}',
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
                            color: Colors.white.withValues(alpha: 0.25),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            '${reward.level} ${context.trRole('donor')}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Environmental Impact Metrics
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text('${context.tr('co2_saved')} 🌿', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
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
                              Text(context.tr('co2_saved'), style: const TextStyle(fontSize: 12, color: Color(0xFF047857))),
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

