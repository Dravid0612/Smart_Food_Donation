import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/primary_action_button.dart';

/// Interactive visual walkthrough explaining the 7-step rescue lifecycle
class HowItWorksScreen extends StatelessWidget {
  const HowItWorksScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final steps = [
      {
        'step': '1',
        'title': context.tr('step1_donor_post'),
        'icon': Icons.post_add_outlined,
        'color': AppTheme.primaryGreen,
        'desc': context.tr('donate_surplus_desc'),
      },
      {
        'step': '2',
        'title': context.tr('ai_vision_analysis'),
        'icon': Icons.auto_awesome_outlined,
        'color': AppTheme.info,
        'desc': context.tr('visual_condition'),
      },
      {
        'step': '3',
        'title': context.tr('step2_ngo_match'),
        'icon': Icons.business_outlined,
        'color': AppTheme.secondaryTerracotta,
        'desc': context.tr('why_match'),
      },
      {
        'step': '4',
        'title': context.tr('step3_volunteer_assign'),
        'icon': Icons.two_wheeler_outlined,
        'color': AppTheme.statusAssigned,
        'desc': context.tr('assigned_volunteer'),
      },
      {
        'step': '5',
        'title': context.tr('step4_pickup_otp'),
        'icon': Icons.local_shipping_outlined,
        'color': AppTheme.warning,
        'desc': context.tr('otp_handover_title'),
      },
      {
        'step': '6',
        'title': context.tr('step5_delivery_distrib'),
        'icon': Icons.volunteer_activism_outlined,
        'color': AppTheme.success,
        'desc': context.tr('status_delivered'),
      },
      {
        'step': '7',
        'title': context.tr('impact_dashboard'),
        'icon': Icons.insights_outlined,
        'color': AppTheme.primaryDark,
        'desc': context.tr('impact_summary'),
      },
    ];

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('how_it_works')),
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
              Container(
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: AppTheme.primaryGreen.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.2)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, color: AppTheme.primaryGreen, size: 24),
                    const SizedBox(width: AppTheme.space12),
                    Expanded(
                      child: Text(
                        context.tr('how_it_works_subtitle'),
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.primaryDark),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space20),

              // Step List
              ...List.generate(steps.length, (index) {
                final s = steps[index];
                final isLast = index == steps.length - 1;
                final color = s['color'] as Color;

                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Step Number Column with Line
                    Column(
                      children: [
                        Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: color,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(color: color.withValues(alpha: 0.3), blurRadius: 6, offset: const Offset(0, 2)),
                            ],
                          ),
                          child: Center(
                            child: Text(
                              '${index + 1}',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                            ),
                          ),
                        ),
                        if (!isLast)
                          Container(
                            width: 2,
                            height: 70,
                            color: AppTheme.border,
                          ),
                      ],
                    ),
                    const SizedBox(width: AppTheme.space16),

                    // Card Content
                    Expanded(
                      child: Container(
                        margin: const EdgeInsets.only(bottom: AppTheme.space16),
                        padding: const EdgeInsets.all(AppTheme.space16),
                        decoration: BoxDecoration(
                          color: AppTheme.card,
                          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                          border: Border.all(color: AppTheme.border),
                          boxShadow: AppTheme.shadowCard,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  '${context.tr('step_progress', {'current': '${index + 1}', 'total': '7'})}:',
                                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: color, letterSpacing: 0.5),
                                ),
                                const SizedBox(width: 8),
                                Icon(s['icon'] as IconData, size: 16, color: color),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              s['title'] as String,
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              s['desc'] as String,
                              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, height: 1.4),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                );
              }),

              const SizedBox(height: AppTheme.space16),
              PrimaryActionButton(
                label: context.tr('donate_now').toUpperCase(),
                icon: Icons.add_circle_outline,
                onPressed: () => context.push('/donor/create'),
              ),
              const SizedBox(height: AppTheme.space20),
            ],
          ),
        ),
      ),
    );
  }
}
