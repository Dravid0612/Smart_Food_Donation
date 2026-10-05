import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/admin_provider.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';

/// Admin Screen for inspecting and gating NGO shelter verification applications.
class NgoVerificationScreen extends StatefulWidget {
  const NgoVerificationScreen({super.key});

  @override
  State<NgoVerificationScreen> createState() => _NgoVerificationScreenState();
}

class _NgoVerificationScreenState extends State<NgoVerificationScreen> {
  String _selectedFilter = 'Pending'; // Pending, Verified, All

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AdminProvider>(context, listen: false).fetchAllNgos();
    });
  }

  void _showRejectDialog(BuildContext context, dynamic ngo) {
    final reasonController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.card,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusCard)),
        title: Text('${context.tr('reject')} ${ngo.organizationName}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Mandatory Rejection Reason:',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                hintText: 'e.g. Incomplete registration documents, unreachable facility address',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(context.tr('cancel')),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error, foregroundColor: Colors.white),
            onPressed: () async {
              final reason = reasonController.text.trim();
              if (reason.length < 3) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Please enter a valid rejection reason (minimum 3 characters).')),
                );
                return;
              }
              Navigator.pop(ctx);
              final adminProv = Provider.of<AdminProvider>(context, listen: false);
              final ok = await adminProv.rejectNgo(ngo.id, reason: reason);
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(ok ? 'NGO application rejected.' : 'Failed to reject NGO.'),
                    backgroundColor: ok ? AppTheme.primaryGreen : AppTheme.error,
                  ),
                );
              }
            },
            child: Text(context.tr('reject')),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);

    final allNgos = adminProv.allNgos;
    final displayedNgos = _selectedFilter == 'Pending'
        ? allNgos.where((n) => !n.isVerified).toList()
        : _selectedFilter == 'Verified'
            ? allNgos.where((n) => n.isVerified).toList()
            : allNgos;

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
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space8),
                  child: Row(
                    children: ['Pending', 'Verified', 'All'].map((tab) {
                      final isSelected = _selectedFilter == tab;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: FilterChip(
                          label: Text(tab),
                          selected: isSelected,
                          onSelected: (_) => setState(() => _selectedFilter = tab),
                          selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.2),
                          labelStyle: TextStyle(
                            color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
                            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                            fontSize: 12,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
                Expanded(
                  child: displayedNgos.isEmpty
                      ? EmptyStateWidget(
                          icon: Icons.verified_user_outlined,
                          title: context.tr('verified_partner'),
                          description: _selectedFilter == 'Pending'
                              ? 'No pending NGO applications at this time.'
                              : context.tr('verified_partner'),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(AppTheme.space16),
                          itemCount: displayedNgos.length,
                          itemBuilder: (context, index) {
                            final ngo = displayedNgos[index];
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
                                          color: ngo.isVerified
                                              ? AppTheme.primaryGreen.withValues(alpha: 0.12)
                                              : AppTheme.warning.withValues(alpha: 0.12),
                                          shape: BoxShape.circle,
                                        ),
                                        child: Icon(
                                          Icons.business,
                                          color: ngo.isVerified ? AppTheme.primaryGreen : AppTheme.warning,
                                          size: 24,
                                        ),
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
                                            const SizedBox(height: 2),
                                            Text(
                                              '${context.tr('capacity_kg')}: ${ngo.capacity}',
                                              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                            ),
                                          ],
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: ngo.isVerified
                                              ? AppTheme.primaryGreen.withValues(alpha: 0.12)
                                              : AppTheme.warning.withValues(alpha: 0.12),
                                          borderRadius: BorderRadius.circular(6),
                                        ),
                                        child: Text(
                                          ngo.isVerified ? 'Verified' : 'Pending',
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.bold,
                                            color: ngo.isVerified ? AppTheme.primaryDark : const Color(0xFFC05621),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: AppTheme.space12),
                                  Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Icon(Icons.location_on_outlined, size: 16, color: AppTheme.textSecondary),
                                      const SizedBox(width: 6),
                                      Expanded(
                                        child: Text(
                                          'Address: ${ngo.address?.isNotEmpty == true ? ngo.address! : "Not provided"}',
                                          style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  Row(
                                    children: [
                                      const Icon(Icons.phone_outlined, size: 16, color: AppTheme.textSecondary),
                                      const SizedBox(width: 6),
                                      Expanded(
                                        child: Text(
                                          'Phone: ${ngo.contactPhone?.isNotEmpty == true ? ngo.contactPhone! : "Not provided"}',
                                          style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  Row(
                                    children: [
                                      const Icon(Icons.schedule_outlined, size: 16, color: AppTheme.textSecondary),
                                      const SizedBox(width: 6),
                                      Expanded(
                                        child: Text(
                                          'Hours: ${ngo.operatingHours != null ? ngo.operatingHours.toString() : "Not provided"}',
                                          style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (!ngo.isVerified) ...[
                                    const Divider(color: AppTheme.border, height: AppTheme.space24),
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.end,
                                      children: [
                                        OutlinedButton(
                                          onPressed: () => _showRejectDialog(context, ngo),
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
                                            final ok = await adminProv.verifyNgo(ngo.id);
                                            if (ok && mounted) {
                                              messenger.showSnackBar(
                                                SnackBar(
                                                  content: Text(verifiedText),
                                                  backgroundColor: AppTheme.primaryGreen,
                                                ),
                                              );
                                            }
                                          },
                                          style: ElevatedButton.styleFrom(
                                            minimumSize: const Size(0, 38),
                                            backgroundColor: AppTheme.primaryGreen,
                                            foregroundColor: Colors.white,
                                          ),
                                          icon: const Icon(Icons.check_circle_outline, size: 18),
                                          label: const Text('Verify NGO'),
                                        ),
                                      ],
                                    ),
                                  ],
                                ],
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
      bottomNavigationBar: const RoleBottomNav(currentRole: 'admin', currentIndex: 3),
    );
  }
}
