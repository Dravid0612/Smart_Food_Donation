import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/donation_status_timeline.dart';
import '../../widgets/rescue_checklist_widget.dart';
import '../../widgets/condition_badge.dart';
import '../../widgets/urgency_badge.dart';
import '../../widgets/trust_badge.dart';
import '../../widgets/privacy_location_card.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/rescue_ring.dart';
import '../../widgets/rescue_feedback_card.dart';
import '../../widgets/report_problem_dialog.dart';
import '../../core/utils/food_rescue_status_helper.dart';
import '../../screens/donor/pickup_otp_screen.dart';
import '../../screens/auth/phone_verification_screen.dart';

/// Donor Donation Detail Screen featuring visual timeline and transparent rescue tracking.
class DonationDetailScreen extends StatefulWidget {
  final int donationId;
  const DonationDetailScreen({super.key, required this.donationId});

  @override
  State<DonationDetailScreen> createState() => _DonationDetailScreenState();
}

class _DonationDetailScreenState extends State<DonationDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<DonationProvider>(context, listen: false).fetchDonationDetail(widget.donationId);
    });
  }

  void _showCancelDialog(BuildContext context, int donationId) {
    String selectedReason = 'Donor unavailable';
    final reasons = [
      'Donor unavailable',
      'Food spoiled / expired',
      'Quantity mismatch',
      'Kitchen operational issue',
      'Other reason'
    ];

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: AppTheme.card,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Text(context.tr('cancel'), style: const TextStyle(fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Please select a reason for cancelling this rescue:',
                style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: 12),
              Column(
                children: reasons.map((r) {
                  final isSelected = selectedReason == r;
                  return InkWell(
                    onTap: () => setDialogState(() => selectedReason = r),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Icon(
                            isSelected ? Icons.radio_button_checked : Icons.radio_button_off,
                            color: isSelected ? AppTheme.error : AppTheme.textSecondary,
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Expanded(child: Text(r, style: const TextStyle(fontSize: 13))),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text(context.tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
            ),
            ElevatedButton(
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(context);
                final cancelledText = context.tr('status_cancelled');
                final errText = context.trError('err_server');
                Navigator.pop(ctx);
                final prov = Provider.of<DonationProvider>(context, listen: false);
                final ok = await prov.cancelDonation(donationId, selectedReason);
                if (mounted) {
                  messenger.showSnackBar(
                    SnackBar(content: Text(ok ? cancelledText : errText)),
                  );
                }
              },
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
              child: Text(context.tr('confirm'), style: const TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _shareViaWhatsApp(BuildContext context, dynamic item) async {
    final prov = Provider.of<DonationProvider>(context, listen: false);
    final claimUrl = await prov.generateClaimToken(item.id);
    if (!context.mounted) return;
    final fullLink = 'https://smartfoodrescue.org${claimUrl ?? "/claim/${item.id}"}';
    final shareMsg = context.tr('share_whatsapp_msg', {
      'food': context.trFood(item.foodName),
      'qty': '${item.quantity.toInt()} ${context.trUnit(item.quantityUnit)}',
      'location': item.pickupAddress,
      'link': fullLink,
    });

    final uri = Uri.parse('whatsapp://send?text=${Uri.encodeComponent(shareMsg)}');
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        await Clipboard.setData(ClipboardData(text: '$shareMsg\n$fullLink'));
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(context.tr('claim_link_copied')),
              backgroundColor: AppTheme.primaryGreen,
            ),
          );
        }
      }
    } catch (_) {
      await Clipboard.setData(ClipboardData(text: '$shareMsg\n$fullLink'));
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.tr('claim_link_copied')),
            backgroundColor: AppTheme.primaryGreen,
          ),
        );
      }
    }
  }

  void _confirmSelfDropoff(BuildContext context, int donationId) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.card,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Icon(Icons.directions_walk_rounded, color: AppTheme.primaryGreen, size: 24),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                context.tr('self_dropoff_confirm'),
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
          ],
        ),
        content: Text(
          context.tr('self_dropoff_desc'),
          style: const TextStyle(fontSize: 13, height: 1.4),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(context.tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final prov = Provider.of<DonationProvider>(context, listen: false);
              final ok = await prov.selfDropoffDonation(donationId);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(ok ? context.tr('self_dropoff_success') : 'Failed to switch pickup mode.'),
                    backgroundColor: ok ? AppTheme.primaryGreen : AppTheme.error,
                  ),
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryGreen,
              foregroundColor: Colors.white,
            ),
            child: Text(context.tr('confirm')),
          ),
        ],
      ),
    );
  }

  String _formatTimeRemaining(String? expiryStr) {
    if (expiryStr == null) return '4h left';
    final expiry = DateTime.tryParse(expiryStr);
    if (expiry == null) return '4h left';
    final diff = expiry.difference(DateTime.now());
    if (diff.isNegative) return context.tr('status_expired');
    if (diff.inHours > 0) return '${diff.inHours}h';
    return '${diff.inMinutes}m';
  }

  String _getNextStepDescription(BuildContext context, String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return context.tr('why_match');
      case 'accepted':
        return context.tr('assigned_volunteer');
      case 'volunteer_assigned':
        return context.tr('assigned_volunteer');
      case 'collected':
        return context.tr('status_picked_up');
      case 'delivered':
        return context.tr('status_delivered');
      case 'completed':
        return context.tr('status_completed');
      default:
        return context.trStatus(status);
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<DonationProvider>(context);
    final item = provider.currentDetail;

    if (provider.isLoading || item == null) {
      return Scaffold(
        appBar: AppBar(title: Text(context.tr('donation_details'))),
        body: LoadingStateWidget(message: context.tr('processing')),
      );
    }

    final isPending = item.status.toLowerCase() == 'pending';
    final isAccepted = ['accepted', 'volunteer_assigned'].contains(item.status.toLowerCase());
    final isDelivered = ['delivered', 'completed'].contains(item.status.toLowerCase());
    final isArrivedAtDonor = item.status.toLowerCase() == 'arrived_at_donor';
    final timeRemaining = _formatTimeRemaining(item.expiryTime);

    // Current user role
    final authProvider = context.watch<AuthProvider>();
    final isDonor = authProvider.user?.role == 'donor';
    final donorPhoneVerified = authProvider.user?.phoneVerified ?? false;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('donation_details')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        actions: [
          if (['pending', 'accepted', 'volunteer_assigned', 'pickup_en_route', 'arrived_at_donor'].contains(item.status.toLowerCase()))
            IconButton(
              icon: const Icon(Icons.cancel_outlined, color: AppTheme.error),
              tooltip: context.tr('cancel'),
              onPressed: () => _showCancelDialog(context, item.id),
            ),
          IconButton(
            icon: const Icon(Icons.flag_outlined),
            tooltip: context.tr('report_problem'),
            onPressed: () {
              showDialog(
                context: context,
                builder: (ctx) => ReportProblemDialog(
                  donationId: item.id,
                  currentRole: 'donor',
                ),
              );
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTheme.space16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── PICKUP OTP BANNER: shown when volunteer has arrived ─────────
            if (isDonor && isArrivedAtDonor) ..._buildPickupOtpBanner(
              context, item.id, donorPhoneVerified,
            ),

            // ── Header Card: Food Name & Quantity ───────────────────────────
            Container(
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
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              context.trFood(item.foodName),
                              style: const TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.textPrimary,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '${item.quantity.toInt()} ${context.trUnit(item.quantityUnit)}',
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.primaryGreen,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: AppTheme.space12),
                      RescueRing.compact(
                        remainingMinutes: item.remainingMinutes ??
                            FoodRescueStatusHelper.calculateRemainingMinutes(item.expiryTime),
                        urgencyOverride: item.urgencyLevel,
                      ),
                    ],
                  ),
                  const SizedBox(height: AppTheme.space12),
                  Wrap(
                    spacing: AppTheme.space8,
                    runSpacing: AppTheme.space4,
                    children: [
                      if (item.aiVisualCondition != null && item.aiVisualCondition!.isNotEmpty)
                        ConditionBadge(
                          condition: item.aiVisualCondition!,
                          confidence: item.aiConfidenceScore,
                        ),
                      UrgencyBadge(
                        level: item.urgencyLevel,
                        remainingMinutes: item.remainingMinutes ??
                            FoodRescueStatusHelper.calculateRemainingMinutes(item.expiryTime),
                      ),
                      TrustBadge(label: context.tr('verified_partner'), isVerified: true),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppTheme.space16),

            // ── Dynamic Rematching Reassurance Banner ───────────────────────
            if (item.isRematched || item.rematchCount > 0) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: AppTheme.info.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.info.withValues(alpha: 0.4), width: 1.2),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.info.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.swap_horiz_rounded, color: AppTheme.info, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.tr('rematch_banner_title'),
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.info,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            context.tr('rematch_banner_desc'),
                            style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, height: 1.3),
                          ),
                          if (item.previousVolunteerName != null) ...[
                            const SizedBox(height: 6),
                            Text(
                              'Prior Courier: ${item.previousVolunteerName} ➔ Assigned: ${item.volunteerName ?? "Assigned"}',
                              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.textSecondary),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),
            ],

            // ── Live Real-Time Rescue Tracking & Honest ETA Card ────────────
            Container(
              padding: const EdgeInsets.all(AppTheme.space16),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
                boxShadow: AppTheme.shadowCard,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.navigation_rounded, color: AppTheme.primaryGreen, size: 20),
                          const SizedBox(width: AppTheme.space8),
                          Text(
                            context.tr('tracking_title'),
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textPrimary),
                          ),
                        ],
                      ),
                      if (item.currentEtaMinutes != null)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryGreen.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.directions_bike_rounded, color: AppTheme.primaryGreen, size: 14),
                              const SizedBox(width: 4),
                              Text(
                                '${item.currentEtaMinutes!.toInt()} min (${context.tr('tracking_eta_label')})',
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: AppTheme.primaryGreen,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                  const Divider(height: AppTheme.space20),

                  _buildTrackingDetailRow('📍 ${context.tr('pickup_address')}', item.pickupAddress),
                  const SizedBox(height: 8),
                  _buildTrackingDetailRow('🤝 ${context.tr('role_ngo')}', item.ngoName ?? (isPending ? context.tr('processing') : context.tr('role_ngo'))),
                  const SizedBox(height: 8),
                  _buildTrackingDetailRow(
                    '🛵 ${context.tr('assigned_volunteer')}',
                    item.volunteerName != null
                        ? '${item.volunteerName} (${item.volunteerPhone ?? context.tr('in_progress')})'
                        : (isPending ? context.tr('processing') : context.tr('assigned_volunteer')),
                  ),
                  const SizedBox(height: 8),
                  _buildTrackingDetailRow('⏱️ ${context.tr('status')}', _getNextStepDescription(context, item.status)),

                  if (item.currentDistanceKm != null) ...[
                    const SizedBox(height: 8),
                    _buildTrackingDetailRow(
                      '📏 ${context.tr('tracking_distance')}',
                      '~${item.currentDistanceKm!.toStringAsFixed(1)} km',
                    ),
                  ],

                  // Periodic battery optimization notice
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceWarm,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.battery_charging_full_rounded, size: 13, color: AppTheme.textSecondary),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            context.tr('tracking_battery_note'),
                            style: const TextStyle(fontSize: 10.5, color: AppTheme.textSecondary),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Food Safety Declaration Badge
                  if (item.safetyCheckCompleted) ...[
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        const Icon(Icons.check_circle_outline, color: AppTheme.success, size: 14),
                        const SizedBox(width: 6),
                        Text(
                          '${context.tr('safety_review_declaration')} ✓',
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.success),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: AppTheme.space16),

            // ── Progressive Disclosure Handover Card ────────────────────────
            if (item.status == 'arrived_at_donor') ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: const Color(0xFF10B981), width: 1.5),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF10B981).withValues(alpha: 0.1),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.location_on, color: Color(0xFF10B981), size: 22),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            context.tr('volunteer_arrived_title').toUpperCase(),
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF10B981),
                              letterSpacing: 1.0,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      context.tr('volunteer_arrived_desc'),
                      style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                    ),
                    const SizedBox(height: 16),
                    // Plaintext OTP revealed on screen with explicit guidance
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFF10B981), width: 2),
                      ),
                      child: Text(
                        item.verificationOtp?.isNotEmpty == true ? item.verificationOtp! : '••••',
                        style: const TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 6.0,
                          color: Color(0xFF065F46),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      context.tr('pickup_code_warning'),
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF065F46),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextButton.icon(
                      onPressed: () => context.push('/donor/otp/${item.id}'),
                      icon: const Icon(Icons.qr_code_2_rounded, size: 18),
                      label: Text(context.tr('show_pickup_code')),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),
            ] else if (item.status == 'pickup_en_route') ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: const Color(0xFF38BDF8).withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.delivery_dining, color: Color(0xFF38BDF8), size: 22),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            context.tr('volunteer_on_the_way_title'),
                            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF38BDF8)),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      context.tr('volunteer_on_the_way_desc'),
                      style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                    ),
                    const SizedBox(height: 14),
                    Center(
                      child: Column(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: const Color(0xFF38BDF8)),
                            ),
                            child: Text(
                              item.verificationOtp?.isNotEmpty == true ? item.verificationOtp! : '••••',
                              style: const TextStyle(
                                fontSize: 26,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 4.0,
                                color: Color(0xFF0369A1),
                              ),
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            context.tr('pickup_code_warning'),
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontSize: 11, color: Color(0xFF0369A1), fontWeight: FontWeight.w500),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),
            ] else if (['accepted', 'volunteer_assigned'].contains(item.status)) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.schedule, color: AppTheme.textSecondary, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.tr('pickup_scheduled'),
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            context.tr('how_step_5_desc'),
                            style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: () => context.push('/donor/otp/${item.id}'),
                      child: Text(context.tr('details'), style: const TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),
            ],

            // ── AI Visual Assessment Studio & Mandatory Disclaimer ──────────
            if (item.aiVisualCondition != null) ...[
              Container(
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
                        const Icon(Icons.auto_awesome, color: AppTheme.primaryGreen, size: 18),
                        const SizedBox(width: AppTheme.space8),
                        Text(
                          context.tr('ai_vision_analysis'),
                          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppTheme.space8),
                    Text(
                      '${context.tr('visual_condition')}: ${context.trVisual(item.aiVisualCondition!)} • ${context.tr('packaging_condition')}: ${item.packagingCondition ?? "Intact"}',
                      style: const TextStyle(fontSize: 13, color: AppTheme.textPrimary),
                    ),
                    const SizedBox(height: AppTheme.space8),
                    Container(
                      padding: const EdgeInsets.all(AppTheme.space8),
                      decoration: BoxDecoration(
                        color: AppTheme.warning.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                        border: Border.all(color: AppTheme.warning.withValues(alpha: 0.3)),
                      ),
                      child: Text(
                        context.trDisclaimer(),
                        style: const TextStyle(fontSize: 11, color: AppTheme.warning, fontWeight: FontWeight.bold, height: 1.3),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),
            ],

            // ── Phase 11: "WHAT HAPPENED TO MY FOOD?" Post-Completion Card ─
            if (isDelivered) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                  border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.35)),
                  boxShadow: AppTheme.shadowCard,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: const BoxDecoration(color: AppTheme.successLight, shape: BoxShape.circle),
                          child: const Icon(Icons.task_alt, color: AppTheme.success, size: 20),
                        ),
                        const SizedBox(width: AppTheme.space12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                context.tr('status_completed').toUpperCase(),
                                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen, letterSpacing: 0.3),
                              ),
                              Text(context.tr('impact_summary'), style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const Divider(height: 24),
                    _buildTrackingDetailRow(context.tr('food_item'), '#${item.id} • ${context.trFood(item.foodName)}'),
                    const SizedBox(height: 6),
                    _buildTrackingDetailRow(context.tr('quantity'), '${item.quantity.toInt()} ${context.trUnit(item.quantityUnit)}'),
                    const SizedBox(height: 6),
                    _buildTrackingDetailRow(context.tr('role_ngo'), item.ngoName ?? 'Partner Shelter NGO'),
                    const SizedBox(height: 6),
                    _buildTrackingDetailRow(context.tr('status'), context.trStatus(item.status)),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),

              // ── Operational Rescue Feedback Card ──────────────────────────
              RescueFeedbackCard(
                donationId: item.id,
                currentRole: 'donor',
                onFeedbackSubmitted: () {
                  Provider.of<DonationProvider>(context, listen: false).fetchDonationDetail(item.id);
                },
              ),
              const SizedBox(height: AppTheme.space16),
            ] else if (['cancelled', 'failed', 'expired'].contains(item.status)) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.secondaryTerracotta.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.help_outline_rounded, color: AppTheme.secondaryTerracotta),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(context.tr('what_went_wrong'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                          Text(context.tr('rate_experience_sub'), style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: () {
                        showDialog(
                          context: context,
                          builder: (ctx) => ReportProblemDialog(
                            donationId: item.id,
                            currentRole: 'donor',
                          ),
                        );
                      },
                      child: Text(context.tr('report_problem'), style: const TextStyle(fontSize: 12, color: AppTheme.secondaryTerracotta, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),
            ],

            // ── Phase 9: "WHY THIS MATCH?" Transparency Card ────────────────
            if (isAccepted) ...[
              Container(
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
                        const Icon(Icons.hub_outlined, color: AppTheme.primaryGreen, size: 18),
                        const SizedBox(width: 8),
                        Text(context.tr('why_match').toUpperCase(), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen, letterSpacing: 0.5)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    _buildMatchFactor('✓ ${context.trCategory(item.foodCategory)}'),
                    _buildMatchFactor('✓ ${context.trMealsCount(item.quantity.toInt())}'),
                    _buildMatchFactor('✓ ${context.tr('verified_partner')}'),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space16),
            ],

            // ── Status Timeline ─────────────────────────────────────────────
            DonationStatusTimeline(
              status: item.status,
              failureReason: item.failureReason,
            ),
            const SizedBox(height: AppTheme.space16),

            // ── Rescue Feasibility Checklist ────────────────────────────────
            RescueChecklistWidget(
              demandMatched: true,
              ngoOpen: true,
              capacityAvailable: true,
              volunteerTransitFit: item.quantity <= 100,
              expiryWindow: '${context.tr('rescue_window')}: $timeRemaining',
              isTightDeadline: item.urgencyLevel == 'Urgent',
            ),
            const SizedBox(height: AppTheme.space16),

            // ── Phase 21: Privacy & Trust Location Card ─────────────────────
            PrivacyLocationCard(
              locationText: item.pickupAddress,
              isExact: true, // Donor always sees their own exact address
            ),
            const SizedBox(height: AppTheme.space20),

            // ── DONOR ACTION HUB (WHATSAPP SHARE & SELF DROP-OFF) ───────────
            if (!['completed', 'delivered', 'cancelled', 'expired'].contains(item.status.toLowerCase())) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space16),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.border),
                  boxShadow: AppTheme.shadowCard,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text(
                      'Rescue Coordination Actions',
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    const SizedBox(height: 12),

                    // WhatsApp Share Button
                    ElevatedButton.icon(
                      onPressed: () => _shareViaWhatsApp(context, item),
                      icon: const Icon(Icons.share, color: Colors.white, size: 18),
                      label: Text(
                        context.tr('share_whatsapp'),
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF25D366), // WhatsApp Green
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                    const SizedBox(height: 10),

                    // Self Drop-off Option
                    if (item.pickupMode != 'self_pickup' && !['collected', 'in_transit'].contains(item.status.toLowerCase()))
                      OutlinedButton.icon(
                        onPressed: () => _confirmSelfDropoff(context, item.id),
                        icon: const Icon(Icons.directions_walk_rounded, size: 18, color: AppTheme.primaryGreen),
                        label: Text(
                          context.tr('self_dropoff'),
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.primaryGreen),
                        ),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: AppTheme.primaryGreen),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space20),
            ],

            // ── Certificate & Record Button ─────────────────────────────────
            if (isDelivered) ...[
              ElevatedButton.icon(
                onPressed: () => context.push('/donor/certificate/${item.id}'),
                icon: const Icon(Icons.verified, color: Colors.white),
                label: Text(
                  context.tr('certificate'),
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryGreen,
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(52),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  elevation: 2,
                ),
              ),
              const SizedBox(height: AppTheme.space24),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTrackingDetailRow(String question, String answer) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(question, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
        const SizedBox(height: 2),
        Text(answer, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
      ],
    );
  }

  Widget _buildMatchFactor(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(
        text,
        style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, height: 1.3),
      ),
    );
  }

  List<Widget> _buildPickupOtpBanner(BuildContext context, int donationId, bool phoneVerified) {
    return [
      Container(
        margin: const EdgeInsets.only(bottom: AppTheme.space16),
        padding: const EdgeInsets.all(AppTheme.space16),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF1E3A8A), Color(0xFF4338CA)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF4338CA).withValues(alpha: 0.3),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.pin_drop, color: Colors.white, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.tr('volunteer_has_arrived') != 'volunteer_has_arrived'
                            ? context.tr('volunteer_has_arrived')
                            : 'Volunteer Has Arrived 📍',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        phoneVerified
                            ? 'Your pickup verification code is ready.'
                            : 'Verify phone number for SMS or view code in app.',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.85),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => PickupOtpScreen(donationId: donationId),
                        ),
                      );
                    },
                    icon: const Icon(Icons.vpn_key_rounded, size: 18),
                    label: Text(
                      context.tr('otp_show_code'),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: const Color(0xFF1E3A8A),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                ),
                if (!phoneVerified) ...[
                  const SizedBox(width: 10),
                  OutlinedButton(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const PhoneVerificationScreen(),
                        ),
                      );
                    },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white70),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: Text(
                      context.tr('verify_phone_action'),
                      style: const TextStyle(fontSize: 12),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    ];
  }
}
