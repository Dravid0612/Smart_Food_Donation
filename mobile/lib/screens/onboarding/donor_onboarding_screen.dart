import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/primary_action_button.dart';

/// 5-Screen First-Time Donor Onboarding Walkthrough with Skip Support
class DonorOnboardingScreen extends StatefulWidget {
  const DonorOnboardingScreen({super.key});

  @override
  State<DonorOnboardingScreen> createState() => _DonorOnboardingScreenState();
}

class _DonorOnboardingScreenState extends State<DonorOnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  final List<Map<String, dynamic>> _slides = [
    {
      'title': 'Why Food Rescue?',
      'subtitle': 'Turn Kitchen Surplus into Community Meals',
      'desc':
          'Good food from events, hotels, and restaurants often goes to waste. Our platform connects eligible surplus with local verified NGOs before the rescue window closes.',
      'icon': Icons.eco_outlined,
      'color': AppTheme.primaryGreen,
    },
    {
      'title': 'How It Works',
      'subtitle': 'Coordinated Pickup & Delivery',
      'desc':
          'Post your surplus in 60 seconds. Our algorithm matches your donation with nearby shelters and dispatches verified volunteer couriers for rapid pickup.',
      'icon': Icons.alt_route_outlined,
      'color': AppTheme.info,
    },
    {
      'title': 'What Information We Need',
      'subtitle': 'Transparent Food & Storage Details',
      'desc':
          'We ask for portion count, preparation timestamp, and continuous storage method to evaluate rescue feasibility and maintain strict food handling standards.',
      'icon': Icons.inventory_2_outlined,
      'color': AppTheme.secondaryTerracotta,
    },
    {
      'title': 'Tracked Handoff & Security',
      'subtitle': 'Single-Use OTP & Direct Updates',
      'desc':
          'You receive a secure 6-digit OTP to verify the volunteer at pickup. Track in-transit progress and receive notification when the NGO records community distribution.',
      'icon': Icons.shield_outlined,
      'color': AppTheme.statusAssigned,
    },
    {
      'title': 'See Your Real Impact',
      'subtitle': 'Transparent Metrics & CSR Records',
      'desc':
          'Follow total meals rescued, verified waste diverted, and receive community Certificates of Participation for every completed rescue.',
      'icon': Icons.insights_outlined,
      'color': AppTheme.success,
    },
  ];

  void _onNext() {
    if (_currentPage < _slides.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    } else {
      _finishOnboarding();
    }
  }

  void _finishOnboarding() {
    context.go('/donor');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          TextButton(
            onPressed: _finishOnboarding,
            child: const Text('SKIP', style: TextStyle(fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                itemCount: _slides.length,
                onPageChanged: (idx) => setState(() => _currentPage = idx),
                itemBuilder: (context, index) {
                  final s = _slides[index];
                  final color = s['color'] as Color;

                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppTheme.space24),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          width: 100,
                          height: 100,
                          decoration: BoxDecoration(
                            color: color.withValues(alpha: 0.12),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(s['icon'] as IconData, size: 50, color: color),
                        ),
                        const SizedBox(height: AppTheme.space32),
                        Text(
                          s['title'] as String,
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                        ),
                        const SizedBox(height: AppTheme.space8),
                        Text(
                          s['subtitle'] as String,
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: color),
                        ),
                        const SizedBox(height: AppTheme.space16),
                        Text(
                          s['desc'] as String,
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 14, color: AppTheme.textSecondary, height: 1.5),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),

            // Indicator Dots & Bottom Action
            Padding(
              padding: const EdgeInsets.all(AppTheme.space24),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(_slides.length, (idx) {
                      final isSelected = idx == _currentPage;
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        width: isSelected ? 24 : 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: isSelected ? AppTheme.primaryGreen : AppTheme.border,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      );
                    }),
                  ),
                  const SizedBox(height: AppTheme.space24),
                  PrimaryActionButton(
                    label: _currentPage == _slides.length - 1 ? 'START FIRST DONATION' : 'CONTINUE',
                    onPressed: _onNext,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
