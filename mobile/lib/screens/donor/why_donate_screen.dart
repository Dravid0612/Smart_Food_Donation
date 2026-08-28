import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/primary_action_button.dart';

/// Professional "Why Donate?" Screen explaining the value, safety, and community purpose of food rescue.
class WhyDonateScreen extends StatelessWidget {
  const WhyDonateScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('why_donate')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppTheme.space16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Hero Headline
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space20),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppTheme.primaryGreen, AppTheme.primaryDark],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                  boxShadow: AppTheme.shadowCard,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                      ),
                      child: Text(
                        context.tr('why_donate').toUpperCase(),
                        style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                      ),
                    ),
                    const SizedBox(height: AppTheme.space12),
                    Text(
                      context.tr('tagline'),
                      style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold, height: 1.3),
                    ),
                    const SizedBox(height: AppTheme.space8),
                    Text(
                      context.tr('donate_surplus_desc'),
                      style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.4),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space20),

              // Section 1: Reduce Avoidable Food Waste
              _buildSectionCard(
                icon: Icons.eco_outlined,
                iconColor: AppTheme.primaryGreen,
                title: '1. ${context.tr('co2_saved')}',
                subtitle: context.tr('donate_surplus_desc'),
                bullets: [
                  context.tr('donate_surplus_desc'),
                  context.tr('why_match'),
                ],
              ),
              const SizedBox(height: AppTheme.space16),

              // Section 2: Connect with Verified Community Organizations
              _buildSectionCard(
                icon: Icons.handshake_outlined,
                iconColor: AppTheme.secondaryTerracotta,
                title: '2. ${context.tr('role_ngo')}',
                subtitle: context.tr('why_match'),
                bullets: [
                  context.tr('verified_partner'),
                  context.tr('capacity_kg'),
                ],
              ),
              const SizedBox(height: AppTheme.space16),

              // Section 3: Coordinated Rescue Workflow
              _buildSectionCard(
                icon: Icons.alt_route_outlined,
                iconColor: AppTheme.info,
                title: '3. ${context.tr('how_it_works')}',
                subtitle: context.tr('how_it_works_subtitle'),
                bullets: [
                  context.tr('step1_donor_post'),
                  context.tr('step2_ngo_match'),
                  context.tr('step3_volunteer_assign'),
                ],
              ),
              const SizedBox(height: AppTheme.space16),

              // Section 4: Measure Your Impact & CSR Records
              _buildSectionCard(
                icon: Icons.insights_outlined,
                iconColor: AppTheme.warning,
                title: '4. ${context.tr('impact_dashboard')}',
                subtitle: context.tr('impact_summary'),
                bullets: [
                  context.tr('meals_rescued'),
                  context.tr('certificate'),
                ],
              ),
              const SizedBox(height: AppTheme.space16),

              // Section 5: Donor Trust & Regulatory Protections (FSSAI)
              Container(
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                  border: Border.all(color: const Color(0xFF3E6E72).withValues(alpha: 0.3)),
                  boxShadow: AppTheme.shadowCard,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: const Color(0xFF3E6E72).withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                          ),
                          child: const Icon(Icons.verified_user_outlined, color: Color(0xFF3E6E72), size: 22),
                        ),
                        const SizedBox(width: AppTheme.space12),
                        Expanded(
                          child: Text(
                            '5. ${context.tr('trust_compliance_title')}',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppTheme.space12),
                    Text(
                      context.tr('fssai_notice'),
                      style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary, height: 1.4),
                    ),
                    const SizedBox(height: AppTheme.space12),
                    Text(
                      context.tr('donor_responsibilities_title'),
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF3E6E72)),
                    ),
                    const SizedBox(height: AppTheme.space8),
                    _buildCheckItem(context.tr('resp_accurate_info')),
                    _buildCheckItem(context.tr('resp_proper_storage')),
                    _buildCheckItem(context.tr('resp_no_spoiled')),
                    const SizedBox(height: AppTheme.space12),
                    Container(
                      padding: const EdgeInsets.all(AppTheme.space10),
                      decoration: BoxDecoration(
                        color: AppTheme.background,
                        borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.info_outline, size: 16, color: AppTheme.textSecondary),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              context.tr('legal_disclaimer_notice'),
                              style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space24),

              // Action Buttons
              PrimaryActionButton(
                label: context.tr('donate_now').toUpperCase(),
                icon: Icons.add_circle_outline,
                onPressed: () => context.push('/donor/create'),
              ),
              const SizedBox(height: AppTheme.space12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => context.push('/donor/how-it-works'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: AppTheme.space14),
                    side: const BorderSide(color: AppTheme.primaryGreen),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                  ),
                  child: Text(context.tr('how_it_works').toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primaryGreen)),
                ),
              ),
              const SizedBox(height: AppTheme.space20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionCard({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required List<String> bullets,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: iconColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                ),
                child: Icon(icon, color: iconColor, size: 22),
              ),
              const SizedBox(width: AppTheme.space12),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space12),
          Text(
            subtitle,
            style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary, height: 1.4),
          ),
          const Divider(height: 24),
          ...bullets.map((b) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.check_circle, size: 14, color: AppTheme.primaryGreen),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        b,
                        style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary, height: 1.3),
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildCheckItem(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_circle, size: 14, color: Color(0xFF3E6E72)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary, height: 1.3),
            ),
          ),
        ],
      ),
    );
  }
}
