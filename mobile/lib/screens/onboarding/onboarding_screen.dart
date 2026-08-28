import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/constants/app_constants.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';

/// 4-Screen Onboarding with First-Time Language Selection
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentIndex = 0;

  Future<void> _completeOnboarding([String? role]) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConstants.keyOnboardingComplete, true);
    if (mounted) {
      if (role != null) {
        context.go('/register', extra: {'role': role});
      } else {
        context.go('/login');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final localeProv = Provider.of<LocaleProvider>(context);

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Column(
          children: [
            // Top Skip Button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space8),
              child: Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () => _completeOnboarding(),
                  child: Text(
                    context.tr('skip_to_login'),
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
            // Slide Pages
            Expanded(
              child: PageView(
                controller: _pageController,
                onPageChanged: (index) => setState(() => _currentIndex = index),
                children: [
                  _buildLanguageScreen(localeProv),
                  _buildScreenOne(),
                  _buildScreenTwo(),
                  _buildScreenThree(),
                ],
              ),
            ),
            // Bottom Indicator & Actions
            Padding(
              padding: const EdgeInsets.all(AppTheme.space24),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: List.generate(
                      4,
                      (index) => AnimatedContainer(
                        duration: const Duration(milliseconds: 250),
                        margin: const EdgeInsets.only(right: 6),
                        height: 8,
                        width: _currentIndex == index ? 24 : 8,
                        decoration: BoxDecoration(
                          color: _currentIndex == index ? AppTheme.primaryGreen : AppTheme.border,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                  ),
                  if (_currentIndex < 3)
                    ElevatedButton(
                      onPressed: () {
                        _pageController.nextPage(
                          duration: const Duration(milliseconds: 300),
                          curve: Curves.easeInOut,
                        );
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryGreen,
                        padding: const EdgeInsets.symmetric(horizontal: AppTheme.space24, vertical: AppTheme.space12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                      ),
                      child: Row(
                        children: [
                          Text(_currentIndex == 0 ? context.tr('continue_btn') : context.tr('next')),
                          const SizedBox(width: 4),
                          const Icon(Icons.arrow_forward, size: 16),
                        ],
                      ),
                    )
                  else
                    ElevatedButton(
                      onPressed: () => _completeOnboarding(),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryGreen,
                        padding: const EdgeInsets.symmetric(horizontal: AppTheme.space24, vertical: AppTheme.space12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                      ),
                      child: Text(context.tr('get_started')),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLanguageScreen(LocaleProvider prov) {
    return Padding(
      padding: const EdgeInsets.all(AppTheme.space24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(AppTheme.space20),
            decoration: BoxDecoration(
              color: AppTheme.primaryGreen.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.language, size: 56, color: AppTheme.primaryGreen),
          ),
          const SizedBox(height: AppTheme.space24),
          Text(
            context.tr('choose_language'),
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppTheme.textPrimary,
              letterSpacing: -0.5,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppTheme.space8),
          Text(
            context.tr('choose_language_sub'),
            style: const TextStyle(
              fontSize: 14,
              color: AppTheme.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppTheme.space24),
          _buildLangTile(prov, 'en', 'English', 'English', 'A'),
          _buildLangTile(prov, 'ta', 'தமிழ்', 'Tamil', 'த'),
          _buildLangTile(prov, 'hi', 'हिन्दी', 'Hindi', 'ह'),
        ],
      ),
    );
  }

  Widget _buildLangTile(LocaleProvider prov, String code, String title, String subtitle, String letter) {
    final isSelected = prov.currentLanguage == code;
    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space12),
      decoration: BoxDecoration(
        color: isSelected ? AppTheme.primaryGreen.withValues(alpha: 0.08) : AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(
          color: isSelected ? AppTheme.primaryGreen : AppTheme.border,
          width: isSelected ? 2 : 1,
        ),
      ),
      child: ListTile(
        onTap: () => prov.setLanguage(code),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        leading: CircleAvatar(
          backgroundColor: isSelected ? AppTheme.primaryGreen : Colors.grey.shade200,
          foregroundColor: isSelected ? Colors.white : Colors.black87,
          child: Text(letter, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        ),
        title: Text(
          title,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
            color: isSelected ? AppTheme.primaryGreen : AppTheme.textPrimary,
          ),
        ),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
        trailing: isSelected
            ? const Icon(Icons.check_circle, color: AppTheme.primaryGreen, size: 24)
            : const Icon(Icons.radio_button_unchecked, color: AppTheme.border, size: 24),
      ),
    );
  }

  Widget _buildScreenOne() {
    return Padding(
      padding: const EdgeInsets.all(AppTheme.space32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(AppTheme.space24),
            decoration: BoxDecoration(
              color: AppTheme.primaryGreen.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.volunteer_activism, size: 72, color: AppTheme.primaryGreen),
          ),
          const SizedBox(height: AppTheme.space32),
          Text(
            context.tr('onboarding_title_1'),
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppTheme.textPrimary,
              letterSpacing: -0.5,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppTheme.space12),
          Text(
            context.tr('onboarding_sub_1'),
            style: const TextStyle(
              fontSize: 15,
              color: AppTheme.textSecondary,
              height: 1.4,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildScreenTwo() {
    return Padding(
      padding: const EdgeInsets.all(AppTheme.space24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            context.tr('onboarding_title_2'),
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: AppTheme.space20),
          _buildJourneyStep('1', context.tr('how_step_1_title'), context.tr('how_step_1_desc'), Icons.camera_alt),
          _buildJourneyStep('2', context.tr('how_step_3_title'), context.tr('how_step_3_desc'), Icons.handshake),
          _buildJourneyStep('3', context.tr('how_step_4_title'), context.tr('how_step_4_desc'), Icons.two_wheeler),
          _buildJourneyStep('4', context.tr('how_step_6_title'), context.tr('how_step_6_desc'), Icons.check_circle),
        ],
      ),
    );
  }

  Widget _buildJourneyStep(String num, String title, String desc, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space10),
      padding: const EdgeInsets.all(AppTheme.space12),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppTheme.primaryGreen.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Icon(icon, size: 18, color: AppTheme.primaryGreen),
            ),
          ),
          const SizedBox(width: AppTheme.space12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
                Text(
                  desc,
                  style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildScreenThree() {
    return Padding(
      padding: const EdgeInsets.all(AppTheme.space24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.tr('choose_participation'),
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: AppTheme.space8),
          Text(
            context.tr('choose_participation_sub'),
            style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
          ),
          const SizedBox(height: AppTheme.space20),
          _buildRoleCard(context.tr('role_donor'), context.tr('role_donor_desc'), Icons.restaurant, 'donor'),
          _buildRoleCard(context.tr('role_ngo'), context.tr('role_ngo_desc'), Icons.home_work_outlined, 'ngo'),
          _buildRoleCard(context.tr('role_volunteer'), context.tr('role_volunteer_desc'), Icons.directions_bike, 'volunteer'),
        ],
      ),
    );
  }

  Widget _buildRoleCard(String title, String subtitle, IconData icon, String roleKey) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppTheme.space12),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space8),
        leading: Container(
          padding: const EdgeInsets.all(AppTheme.space12),
          decoration: BoxDecoration(
            color: AppTheme.primaryGreen.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
          ),
          child: Icon(icon, color: AppTheme.primaryGreen, size: 24),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
        trailing: const Icon(Icons.arrow_forward_ios, size: 14, color: AppTheme.textSecondary),
        onTap: () => _completeOnboarding(roleKey),
      ),
    );
  }
}
