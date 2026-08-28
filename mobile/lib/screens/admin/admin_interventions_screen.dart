import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/intervention_card.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';

class AdminInterventionsScreen extends StatefulWidget {
  const AdminInterventionsScreen({super.key});

  @override
  State<AdminInterventionsScreen> createState() => _AdminInterventionsScreenState();
}

class _AdminInterventionsScreenState extends State<AdminInterventionsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
  }

  Future<void> _loadData() async {
    final prov = Provider.of<DonationProvider>(context, listen: false);
    await prov.fetchDonations();
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final donations = prov.donations;

    // Filter to donations requiring administrative intervention
    final interventionList = donations.where((d) {
      final status = d.status.toLowerCase();
      final isEmergency = d.isEmergency;
      return isEmergency || ['pending', 'pickup_failed', 'delivery_failed'].contains(status);
    }).toList();

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(context.tr('system_interventions'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
            Text(context.tr('role_admin'), style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppTheme.space16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Warning Banner
              Container(
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: AppTheme.warning.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.warning.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: AppTheme.warning, size: 28),
                    const SizedBox(width: AppTheme.space12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.tr('system_interventions'),
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                          Text(
                            '${interventionList.length} ${context.tr('in_progress')}',
                            style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),

              if (prov.isLoading)
                LoadingStateWidget(message: context.tr('processing'))
              else if (interventionList.isEmpty)
                EmptyStateWidget(
                  title: context.tr('no_donations'),
                  description: context.tr('no_donations_desc'),
                  icon: Icons.check_circle_outline,
                )
              else
                ...interventionList.map((donation) => Padding(
                      padding: const EdgeInsets.only(bottom: AppTheme.space12),
                      child: InterventionCard(
                        donation: donation,
                        onEscalate: () async {
                          final messenger = ScaffoldMessenger.of(context);
                          final confirmText = '🚨 ${context.tr('confirm')}!';
                          final ok = await prov.escalateDonation(donation.id);
                          if (mounted && ok) {
                            messenger.showSnackBar(
                              SnackBar(
                                content: Text(confirmText),
                                backgroundColor: AppTheme.secondaryTerracotta,
                              ),
                            );
                            _loadData();
                          }
                        },
                        onReassign: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text(context.tr('confirm'))),
                          );
                        },
                      ),
                    )),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const RoleBottomNav(
        currentRole: 'admin',
        currentIndex: 0,
      ),
    );
  }
}
