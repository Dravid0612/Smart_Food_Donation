import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/admin_provider.dart';
import '../../providers/ngo_provider.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';

/// Admin Screen for inspecting and gating NGO shelter verification applications.
class NgoVerificationScreen extends StatefulWidget {
  const NgoVerificationScreen({super.key});

  @override
  State<NgoVerificationScreen> createState() => _NgoVerificationScreenState();
}

class _NgoVerificationScreenState extends State<NgoVerificationScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AdminProvider>(context, listen: false).fetchAllNgos();
    });
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);
    final ngoProv = Provider.of<NgoProvider>(context);

    final allNgos = adminProv.allNgos;
    final unverifiedNgos = allNgos.where((n) => !n.isVerified).toList();

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('verify_ngos')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: adminProv.isLoading
          ? LoadingStateWidget(message: context.tr('processing'))
          : unverifiedNgos.isEmpty
              ? EmptyStateWidget(
                  icon: Icons.verified_user_outlined,
                  title: context.tr('verified_partner'),
                  description: context.tr('verified_partner'),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(AppTheme.space16),
                  itemCount: unverifiedNgos.length,
                  itemBuilder: (context, index) {
                    final ngo = unverifiedNgos[index];
                    return Container(
                      margin: const EdgeInsets.only(bottom: AppTheme.space12),
                      padding: const EdgeInsets.all(AppTheme.space16),
                      decoration: BoxDecoration(
                        color: AppTheme.card,
                        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(AppTheme.space12),
                                decoration: BoxDecoration(
                                  color: AppTheme.warning.withValues(alpha: 0.12),
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(Icons.business, color: AppTheme.warning, size: 24),
                              ),
                              const SizedBox(width: AppTheme.space12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      ngo.organizationName,
                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.textPrimary),
                                    ),
                                    Text(
                                      '${context.tr('capacity_kg')}: ${ngo.capacity}',
                                      style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: AppTheme.space12),
                          Row(
                            children: [
                              const Icon(Icons.location_on_outlined, size: 16, color: AppTheme.textSecondary),
                              const SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  ngo.address ?? context.tr('pickup_address'),
                                  style: const TextStyle(fontSize: 13, color: AppTheme.textPrimary),
                                ),
                              ),
                            ],
                          ),
                          const Divider(color: AppTheme.border, height: AppTheme.space24),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              OutlinedButton(
                                onPressed: () {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text(context.tr('reject'))),
                                  );
                                },
                                style: OutlinedButton.styleFrom(
                                  minimumSize: const Size(0, 38),
                                  foregroundColor: AppTheme.error,
                                  side: const BorderSide(color: AppTheme.error),
                                ),
                                child: Text(context.tr('reject')),
                              ),
                              const SizedBox(width: AppTheme.space12),
                              ElevatedButton.icon(
                                onPressed: () async {
                                  final messenger = ScaffoldMessenger.of(context);
                                  final verifiedText = '✅ ${ngo.organizationName} ${context.tr('verified_partner')}!';
                                  final ok = await ngoProv.verifyNgo(ngo.id);
                                  if (ok && mounted) {
                                    messenger.showSnackBar(
                                      SnackBar(
                                        content: Text(verifiedText),
                                        backgroundColor: AppTheme.primaryGreen,
                                      ),
                                    );
                                    adminProv.fetchAllNgos();
                                  }
                                },
                                style: ElevatedButton.styleFrom(
                                  minimumSize: const Size(0, 38),
                                  backgroundColor: AppTheme.primaryGreen,
                                  foregroundColor: Colors.white,
                                ),
                                icon: const Icon(Icons.check_circle_outline, size: 18),
                                label: Text(context.tr('confirm')),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
