import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/otp_input_widget.dart';
import '../../widgets/primary_action_button.dart';
import '../../widgets/privacy_location_card.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/rescue_ring.dart';
import '../../widgets/rescue_feedback_card.dart';
import '../../core/utils/food_rescue_status_helper.dart';

/// Volunteer Active Pickup & Delivery Screen with dynamic one-primary-action lifecycle and one-handed OTP entry.
class VolunteerActiveTaskScreen extends StatefulWidget {
  final int donationId;
  const VolunteerActiveTaskScreen({super.key, required this.donationId});

  @override
  State<VolunteerActiveTaskScreen> createState() => _VolunteerActiveTaskScreenState();
}

class _VolunteerActiveTaskScreenState extends State<VolunteerActiveTaskScreen> {
  bool _isLoading = false;
  String? _otpError;

  // Sub-stages for volunteer courier workflow:
  // 0: Assigned, 1: On the Way, 2: Arrived, 3: Picked Up, 4: Delivered
  int _volunteerSubStage = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final donProv = Provider.of<DonationProvider>(context, listen: false);
      donProv.fetchDonationDetail(widget.donationId).then((_) {
        if (!mounted) return;
        final item = donProv.currentDetail;
        if (item != null) {
          if (['collected'].contains(item.status.toLowerCase())) {
            setState(() => _volunteerSubStage = 3);
          } else if (['delivered', 'completed'].contains(item.status.toLowerCase())) {
            setState(() => _volunteerSubStage = 4);
          }
        }
      });
    });
  }

  Future<void> _openMaps(double lat, double lng) async {
    final uri = Uri.parse('https://www.google.com/maps/dir/?api=1&destination=$lat,$lng');
    if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  void _showOtpModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusFeatureCard)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Padding(
          padding: EdgeInsets.only(
            left: AppTheme.space24,
            right: AppTheme.space24,
            top: AppTheme.space24,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + AppTheme.space24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                context.tr('otp_title').toUpperCase(),
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                context.trOtpVolunteer(),
                style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppTheme.space24),
              OtpInputWidget(
                isLoading: _isLoading,
                errorMessage: _otpError,
                onCompleted: (code) async {
                  setModalState(() => _isLoading = true);
                  final taskProv = Provider.of<VolunteerTaskProvider>(context, listen: false);
                  final donProv = Provider.of<DonationProvider>(context, listen: false);
                  final messenger = ScaffoldMessenger.of(context);
                  final nav = Navigator.of(ctx);
                  final verifiedText = '✅ ${context.tr('otp_verified')}!';
                  final defaultErr = context.trError('err_server');
                  final isValid = await taskProv.verifyPickupOtp(widget.donationId, code);
                  if (!mounted) return;
                  setModalState(() => _isLoading = false);

                  if (isValid) {
                    nav.pop();
                    setState(() => _volunteerSubStage = 3);
                    messenger.showSnackBar(
                      SnackBar(
                        content: Text(verifiedText),
                        backgroundColor: AppTheme.primaryGreen,
                      ),
                    );
                    donProv.fetchDonationDetail(widget.donationId);
                  } else {
                    setModalState(() => _otpError = taskProv.errorMessage != null ? context.trError(taskProv.errorMessage!) : defaultErr);
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showReportProblemDialog(BuildContext context, bool isPickup) {
    String selectedReason = 'Donor unavailable';
    final reasons = isPickup
        ? ['Donor unavailable', 'Vehicle issue', 'Food unavailable', 'Incorrect address', 'Other']
        : ['NGO unavailable', 'Vehicle issue', 'Refused by NGO', 'Accident / delay', 'Other'];

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: AppTheme.card,
          title: Text(context.tr('reject'), style: const TextStyle(fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: reasons.map((r) {
              final isSel = selectedReason == r;
              return InkWell(
                onTap: () => setDialogState(() => selectedReason = r),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: AppTheme.space8),
                  child: Row(
                    children: [
                      Icon(
                        isSel ? Icons.radio_button_checked : Icons.radio_button_off,
                        color: isSel ? AppTheme.error : AppTheme.textSecondary,
                        size: 20,
                      ),
                      const SizedBox(width: AppTheme.space12),
                      Expanded(
                        child: Text(
                          r,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
                            color: isSel ? AppTheme.error : AppTheme.textPrimary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),

          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text(context.tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
            ),
            ElevatedButton(
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(context);
                final router = GoRouter.of(context);
                final rejectText = context.tr('reject');
                Navigator.pop(ctx);
                final taskProv = Provider.of<VolunteerTaskProvider>(context, listen: false);
                final ok = await taskProv.reportFailure(
                  donationId: widget.donationId,
                  failureType: isPickup ? 'pickup_failed' : 'delivery_failed',
                  reason: selectedReason,
                );
                if (ok && mounted) {
                  messenger.showSnackBar(
                    SnackBar(content: Text(rejectText), backgroundColor: AppTheme.error),
                  );
                  router.go('/volunteer');
                }
              },
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
              child: Text(context.tr('reject'), style: const TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmDelivery() async {
    setState(() => _isLoading = true);
    final ok = await Provider.of<VolunteerTaskProvider>(context, listen: false).markDelivered(widget.donationId);
    if (!mounted) return;
    setState(() => _isLoading = false);

    if (ok) {
      setState(() => _volunteerSubStage = 4);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('🎉 ${context.tr('status_delivered')}!'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
      context.go('/volunteer');
    }
  }

  @override
  Widget build(BuildContext context) {
    final donationProv = Provider.of<DonationProvider>(context);
    final item = donationProv.currentDetail;

    if (donationProv.isLoading || item == null) {
      return Scaffold(
        appBar: AppBar(title: Text(context.tr('rescue_live_tracking'))),
        body: LoadingStateWidget(message: context.tr('processing')),
      );
    }

    // Check if task was dynamically reassigned
    if (item.status.toLowerCase() == 'reassigned') {
      return Scaffold(
        backgroundColor: AppTheme.background,
        appBar: AppBar(
          title: Text(context.tr('active_rescues')),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.go('/volunteer'),
          ),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppTheme.space24),
            child: Container(
              padding: const EdgeInsets.all(AppTheme.space24),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
                border: Border.all(color: AppTheme.info.withValues(alpha: 0.4)),
                boxShadow: AppTheme.shadowCard,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.info.withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.swap_horiz_rounded, color: AppTheme.info, size: 40),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    context.tr('volunteer_reassigned_title'),
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    context.tr('volunteer_reassigned_desc'),
                    style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary, height: 1.4),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  PrimaryActionButton(
                    label: context.tr('view_my_deliveries'),
                    icon: Icons.assignment_outlined,
                    onPressed: () => context.go('/volunteer'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    final isPickup = _volunteerSubStage < 3;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('active_rescues')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/volunteer'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.report_problem_outlined, color: AppTheme.warning),
            tooltip: context.tr('reject'),
            onPressed: () => _showReportProblemDialog(context, isPickup),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTheme.space16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── 1. ACTIVE TASK SUMMARY CARD ────────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppTheme.space16),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                border: Border.all(color: AppTheme.primaryGreen.withValues(alpha: 0.3)),
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
                              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '${item.quantity.toInt()} ${context.trUnit(item.quantityUnit)}',
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                            ),
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                const Icon(Icons.business, size: 14, color: AppTheme.textSecondary),
                                const SizedBox(width: 4),
                                Expanded(
                                  child: Text(
                                    '${context.tr('role_ngo')}: ${item.ngoName ?? context.tr('role_ngo')}',
                                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, fontWeight: FontWeight.w600),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      RescueRing.compact(
                        remainingMinutes: item.remainingMinutes ??
                            FoodRescueStatusHelper.calculateRemainingMinutes(item.expiryTime),
                        urgencyOverride: item.urgencyLevel,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppTheme.space16),

            // ── 2. TASK TIMELINE ───────────────────────────────────────────
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
                  Text(
                    context.tr('stage_pickup_en_route'),
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                  ),
                  const SizedBox(height: AppTheme.space12),
                  _buildTimelineItem(0, context.tr('status_accepted'), context.tr('assigned_volunteer')),
                  _buildTimelineItem(1, context.tr('stage_pickup_en_route'), context.tr('vol_action_start_pickup')),
                  _buildTimelineItem(2, context.tr('stage_arrived_at_donor'), context.tr('vol_action_verify_otp')),
                  _buildTimelineItem(3, context.tr('stage_in_transit'), context.tr('vol_action_start_delivery')),
                  _buildTimelineItem(4, context.tr('stage_delivered'), context.tr('status_completed'), isLast: true),
                ],
              ),
            ),
            const SizedBox(height: AppTheme.space16),

            // ── 3. PRIVACY LOCATION CARD ───────────────────────────────────
            PrivacyLocationCard(
              locationText: isPickup ? item.pickupAddress : (item.ngoName ?? 'Partner NGO Center'),
              isExact: true,
              contactName: isPickup ? (item.donorName ?? 'Donor') : (item.ngoName ?? 'NGO Contact'),
              contactPhone: isPickup ? item.donorPhone : '+91 98765 43210',
            ),
            const SizedBox(height: AppTheme.space16),

            // ── 4. NAVIGATION SHORTCUTS ────────────────────────────────────
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _openMaps(item.latitude ?? 12.9716, item.longitude ?? 77.5946),
                    icon: const Icon(Icons.navigation_outlined, size: 18),
                    label: Text(context.tr('rescue_live_tracking')),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppTheme.space24),

            // ── 5. DYNAMIC PRIMARY ACTION BUTTON ───────────────────────────
            _buildDynamicPrimaryAction(),
            const SizedBox(height: AppTheme.space16),
          ],
        ),
      ),
    );
  }

  Widget _buildTimelineItem(int stepIndex, String title, String subtitle, {bool isLast = false}) {
    final isCompleted = _volunteerSubStage > stepIndex;
    final isCurrent = _volunteerSubStage == stepIndex;

    Color color;
    Widget icon;

    if (isCompleted) {
      color = AppTheme.success;
      icon = const Icon(Icons.check, size: 12, color: Colors.white);
    } else if (isCurrent) {
      color = AppTheme.secondaryTerracotta;
      icon = Container(width: 6, height: 6, decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle));
    } else {
      color = AppTheme.disabled;
      icon = Container(width: 4, height: 4, decoration: BoxDecoration(color: AppTheme.disabled.withValues(alpha: 0.5), shape: BoxShape.circle));
    }

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 20,
                height: 20,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                child: Center(child: icon),
              ),
              if (!isLast)
                Expanded(
                  child: Container(width: 2, color: isCompleted ? AppTheme.success : AppTheme.border),
                ),
            ],
          ),
          const SizedBox(width: AppTheme.space12),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : AppTheme.space12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: isCurrent ? FontWeight.bold : FontWeight.w600,
                      color: isCurrent ? AppTheme.textPrimary : AppTheme.textSecondary,
                    ),
                  ),
                  Text(subtitle, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDynamicPrimaryAction() {
    final taskProv = Provider.of<VolunteerTaskProvider>(context, listen: false);
    final donProv = Provider.of<DonationProvider>(context, listen: false);

    switch (_volunteerSubStage) {
      case 0:
        return PrimaryActionButton(
          label: context.tr('action_go_to_pickup'),
          icon: Icons.directions_bike,
          isLoading: _isLoading,
          onPressed: () async {
            setState(() => _isLoading = true);
            await taskProv.startPickup(widget.donationId);
            // Transmit volunteer location telemetry
            await donProv.updateVolunteerLocation(
              latitude: 12.9716,
              longitude: 77.5946,
              donationId: widget.donationId,
            );
            if (mounted) {
              setState(() {
                _isLoading = false;
                _volunteerSubStage = 1;
              });
            }
          },
        );
      case 1:
        return PrimaryActionButton(
          label: context.tr('action_arrived'),
          icon: Icons.location_on,
          backgroundColor: AppTheme.secondaryTerracotta,
          isLoading: _isLoading,
          onPressed: () async {
            setState(() => _isLoading = true);
            await taskProv.markArrived(widget.donationId);
            await donProv.updateVolunteerLocation(
              latitude: 12.9716,
              longitude: 77.5946,
              donationId: widget.donationId,
            );
            if (mounted) {
              setState(() {
                _isLoading = false;
                _volunteerSubStage = 2;
              });
            }
          },
        );
      case 2:
        return PrimaryActionButton(
          label: context.tr('action_verify_otp'),
          icon: Icons.pin_outlined,
          onPressed: () => _showOtpModal(context),
        );
      case 3:
        return PrimaryActionButton(
          label: context.tr('action_deliver'),
          icon: Icons.task_alt,
          isLoading: _isLoading,
          onPressed: _confirmDelivery,
        );
      case 4:
      default:
        return Column(
          children: [
            RescueFeedbackCard(
              donationId: widget.donationId,
              currentRole: 'volunteer',
              onFeedbackSubmitted: () {
                setState(() {});
              },
            ),
            const SizedBox(height: AppTheme.space12),
            PrimaryActionButton(
              label: '${context.tr('status_completed')} 🎉',
              backgroundColor: AppTheme.success,
              onPressed: () => context.go('/volunteer'),
            ),
          ],
        );
    }
  }
}
