import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../models/admin_operations_model.dart';
import '../../providers/admin_provider.dart';
import '../../providers/donation_provider.dart';

/// Modal bottom sheet / dialog displaying the complete Food Rescue Details, 9-stage linear food flow tracker,
/// receiving discrepancy analysis, distribution metrics, audit logs, and intervention actions.
class AdminRescueDetailModal extends StatefulWidget {
  final int donationId;

  const AdminRescueDetailModal({super.key, required this.donationId});

  static Future<void> show(BuildContext context, int donationId) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => AdminRescueDetailModal(donationId: donationId),
    );
  }

  @override
  State<AdminRescueDetailModal> createState() => _AdminRescueDetailModalState();
}

class _AdminRescueDetailModalState extends State<AdminRescueDetailModal> {
  bool _isLoading = true;
  AdminRescueDetailModel? _detail;

  @override
  void initState() {
    super.initState();
    _loadDetail();
  }

  Future<void> _loadDetail() async {
    final adminProv = Provider.of<AdminProvider>(context, listen: false);
    final res = await adminProv.fetchRescueDetail(widget.donationId);
    if (mounted) {
      setState(() {
        _detail = res;
        _isLoading = false;
      });
    }
  }

  void _showInterventionDialog() {
    if (_detail == null) return;
    String selectedReason = 'no_volunteer_available';
    final notesController = TextEditingController();

    final reasonOptions = [
      {'code': 'no_volunteer_available', 'label': 'No Volunteer Available'},
      {'code': 'ngo_unavailable', 'label': 'NGO Unavailable / Closed'},
      {'code': 'pickup_delayed', 'label': 'Pickup Delayed'},
      {'code': 'delivery_delayed', 'label': 'Delivery Delayed'},
      {'code': 'food_condition_concern', 'label': 'Food Condition Concern'},
      {'code': 'quantity_mismatch', 'label': 'Quantity Mismatch Discrepancy'},
      {'code': 'transport_failure', 'label': 'Transport Failure'},
      {'code': 'other', 'label': 'Other Operational Issue'},
    ];

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (dialogCtx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusCard)),
          title: Row(
            children: [
              const Icon(Icons.warning_amber_rounded, color: AppTheme.error, size: 24),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  context.tr('admin_intervene'),
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${_detail!.foodName} (Donation #${_detail!.id})',
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: AppTheme.space12),
                Text(
                  context.tr('intervention_reason'),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: AppTheme.space8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    border: Border.all(color: AppTheme.border),
                    borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                    color: AppTheme.surface,
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: selectedReason,
                      isExpanded: true,
                      items: reasonOptions.map((opt) {
                        return DropdownMenuItem<String>(
                          value: opt['code'],
                          child: Text(opt['label']!, style: const TextStyle(fontSize: 13)),
                        );
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) {
                          setDialogState(() => selectedReason = val);
                        }
                      },
                    ),
                  ),
                ),
                const SizedBox(height: AppTheme.space16),
                const Text(
                  'Operational Notes:',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: AppTheme.space8),
                TextField(
                  controller: notesController,
                  maxLines: 3,
                  decoration: InputDecoration(
                    hintText: 'Enter specific instructions or coordinator notes...',
                    hintStyle: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                      borderSide: const BorderSide(color: AppTheme.border),
                    ),
                    contentPadding: const EdgeInsets.all(12),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(context.tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.error,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
              ),
              onPressed: () async {
                Navigator.of(ctx).pop();
                final adminProv = Provider.of<AdminProvider>(context, listen: false);
                final ok = await adminProv.submitIntervention(
                  _detail!.id,
                  selectedReason,
                  notes: notesController.text.trim(),
                );
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(ok ? 'Intervention recorded & logged to audit trail.' : 'Failed to record intervention.'),
                      backgroundColor: ok ? AppTheme.primaryGreen : AppTheme.error,
                    ),
                  );
                  if (ok) _loadDetail();
                }
              },
              child: Text(context.tr('confirm_intervention')),
            ),
          ],
        ),
      ),
    );
  }

  void _showRematchDialog() {
    if (_detail == null) return;
    String selectedReason = 'Courier delayed / rescue at risk';
    final reasons = [
      'Courier delayed / rescue at risk',
      'Vehicle breakdown / courier emergency',
      'Feasibility window closing',
      'Manual admin re-routing',
      'Other operational need',
    ];

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (dialogCtx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusCard)),
          title: Row(
            children: [
              const Icon(Icons.swap_horiz_rounded, color: AppTheme.info, size: 24),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  context.tr('rematch_dialog_title'),
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.tr('rematch_dialog_desc'),
                style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
              ),
              RadioGroup<String>(
                groupValue: selectedReason,
                onChanged: (v) {
                  if (v != null) setDialogState(() => selectedReason = v);
                },
                child: Column(
                  children: reasons.map((r) => RadioListTile<String>(
                    title: Text(r, style: const TextStyle(fontSize: 12.5)),
                    value: r,
                    activeColor: AppTheme.info,
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                  )).toList(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(context.tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.info,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
              ),
              onPressed: () async {
                Navigator.of(ctx).pop();
                final donProv = Provider.of<DonationProvider>(context, listen: false);
                final res = await donProv.triggerRematch(_detail!.id, reason: selectedReason);
                if (mounted) {
                  final ok = res != null;
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(ok ? context.tr('rematch_dialog_success') : 'Failed to execute rematch.'),
                      backgroundColor: ok ? AppTheme.primaryGreen : AppTheme.error,
                    ),
                  );
                  if (ok) _loadDetail();
                }
              },
              child: Text(context.tr('rematch_confirm_btn')),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final maxHeight = MediaQuery.of(context).size.height * 0.90;

    return Container(
      constraints: BoxConstraints(maxHeight: maxHeight),
      decoration: const BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusCard * 1.5)),
      ),
      child: _isLoading
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: CircularProgressIndicator(),
              ),
            )
          : _detail == null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.error_outline, size: 48, color: AppTheme.error),
                        const SizedBox(height: 12),
                        const Text('Unable to load rescue details.', style: TextStyle(fontWeight: FontWeight.bold)),
                        const SizedBox(height: 12),
                        ElevatedButton(
                          onPressed: _loadDetail,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : Column(
                  children: [
                    // Modal Handle Bar
                    Center(
                      child: Container(
                        margin: const EdgeInsets.only(top: 12, bottom: 8),
                        width: 40,
                        height: 4,
                        decoration: BoxDecoration(
                          color: AppTheme.border,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),

                    // Modal Header
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      'Donation #${_detail!.id}',
                                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                                    ),
                                    const SizedBox(width: 8),
                                    _buildUrgencyBadge(_detail!.rescueUrgencyLevel),
                                  ],
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  _detail!.foodName,
                                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () => Navigator.of(context).pop(),
                          ),
                        ],
                      ),
                    ),
                    const Divider(height: 1, color: AppTheme.divider),

                    // Modal Body Content
                    Expanded(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(AppTheme.space16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // ── 1. FOOD & AI CONDITION ASSESSMENT ──
                            _buildSectionHeader('Food & Assessment'),
                            const SizedBox(height: 8),
                            _buildFoodAssessmentCard(),
                            const SizedBox(height: 16),

                            // ── 2. RESCUE WINDOW & ADVISORY NOTICE ──
                            _buildRescueWindowCard(),
                            const SizedBox(height: 16),

                            // ── 3. 9-STEP LINEAR FOOD FLOW TRACKER ──
                            _buildSectionHeader(context.tr('linear_food_flow')),
                            const SizedBox(height: 8),
                            _buildFoodFlowTracker(),
                            const SizedBox(height: 16),

                            // ── 4. RECEIVING & QUANTITY DISCREPANCY ──
                            _buildSectionHeader('Receiving & Intake Verification'),
                            const SizedBox(height: 8),
                            _buildReceivingDiscrepancyCard(),
                            const SizedBox(height: 16),

                            // ── 5. BENEFICIARY DISTRIBUTION ──
                            _buildSectionHeader('Beneficiary Distribution'),
                            const SizedBox(height: 8),
                            _buildDistributionCard(),
                            const SizedBox(height: 16),

                            // ── 6. PARTICIPANT CONTACTS & ROUTE ──
                            _buildSectionHeader('Participants & Route'),
                            const SizedBox(height: 8),
                            _buildParticipantsCard(),
                            const SizedBox(height: 24),

                            // ── 7. ACTION BUTTONS ──
                            Column(
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: OutlinedButton.icon(
                                        style: OutlinedButton.styleFrom(
                                          foregroundColor: AppTheme.info,
                                          side: const BorderSide(color: AppTheme.info),
                                          padding: const EdgeInsets.symmetric(vertical: 14),
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                                        ),
                                        icon: const Icon(Icons.swap_horiz_rounded, size: 18),
                                        label: Text(context.tr('rematch_action_btn'), style: const TextStyle(fontWeight: FontWeight.bold)),
                                        onPressed: _showRematchDialog,
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: OutlinedButton.icon(
                                        style: OutlinedButton.styleFrom(
                                          foregroundColor: AppTheme.error,
                                          side: const BorderSide(color: AppTheme.error),
                                          padding: const EdgeInsets.symmetric(vertical: 14),
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                                        ),
                                        icon: const Icon(Icons.warning_amber_rounded, size: 18),
                                        label: Text(context.tr('admin_intervene'), style: const TextStyle(fontWeight: FontWeight.bold)),
                                        onPressed: _showInterventionDialog,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),
                                SizedBox(
                                  width: double.infinity,
                                  child: ElevatedButton(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: AppTheme.primaryGreen,
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(vertical: 14),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                                    ),
                                    onPressed: () => Navigator.of(context).pop(),
                                    child: const Text('Done', style: TextStyle(fontWeight: FontWeight.bold)),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 16),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.bold,
        color: AppTheme.textPrimary,
        letterSpacing: -0.1,
      ),
    );
  }

  Widget _buildUrgencyBadge(String urgency) {
    Color bg;
    Color fg;
    switch (urgency.toUpperCase()) {
      case 'CRITICAL':
        bg = AppTheme.error.withValues(alpha: 0.12);
        fg = AppTheme.error;
        break;
      case 'URGENT':
        bg = AppTheme.warning.withValues(alpha: 0.15);
        fg = const Color(0xFFC05621);
        break;
      case 'APPROACHING':
        bg = Colors.amber.withValues(alpha: 0.2);
        fg = const Color(0xFF975A16);
        break;
      case 'FRESH':
      default:
        bg = AppTheme.primaryGreen.withValues(alpha: 0.12);
        fg = AppTheme.primaryDark;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        urgency.toUpperCase(),
        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: fg),
      ),
    );
  }

  Widget _buildFoodAssessmentCard() {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space14),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildMetricItem('Quantity', '${_detail!.quantity.toInt()} ${_detail!.quantityUnit}'),
              _buildMetricItem('Category', _detail!.foodCategory),
              _buildMetricItem('Visual Condition', _detail!.aiVisualCondition, color: _getConditionColor(_detail!.aiVisualCondition)),
            ],
          ),
          const Divider(height: AppTheme.space20, color: AppTheme.divider),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildMetricItem('Storage Method', _detail!.storageMethod),
              _buildMetricItem('Packaging', _detail!.packagingCondition),
            ],
          ),
        ],
      ),
    );
  }

  Color _getConditionColor(String condition) {
    switch (condition.toUpperCase()) {
      case 'GOOD':
        return AppTheme.primaryGreen;
      case 'FAIR':
        return const Color(0xFFC05621);
      case 'CONCERNING':
      case 'POOR':
        return AppTheme.error;
      default:
        return AppTheme.textSecondary;
    }
  }

  Widget _buildRescueWindowCard() {
    final rem = _detail!.remainingMinutes ?? 0;
    final isEnded = rem <= 0;

    return Container(
      padding: const EdgeInsets.all(AppTheme.space14),
      decoration: BoxDecoration(
        color: isEnded ? AppTheme.error.withValues(alpha: 0.06) : AppTheme.surface,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: isEnded ? AppTheme.error.withValues(alpha: 0.3) : AppTheme.border),
      ),
      child: Row(
        children: [
          Icon(
            Icons.timer_outlined,
            size: 28,
            color: isEnded ? AppTheme.error : (_detail!.rescueUrgencyLevel == 'CRITICAL' ? AppTheme.error : AppTheme.warning),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isEnded ? 'Rescue Window Ended' : 'Estimated Rescue Window: $rem min remaining',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: isEnded ? AppTheme.error : AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                const Text(
                  'Visual assessment only. Advisory estimation for dispatch optimization.',
                  style: TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFoodFlowTracker() {
    final timeline = _detail!.timeline;
    if (timeline.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(AppTheme.space14),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: timeline.asMap().entries.map((entry) {
          final idx = entry.key;
          final item = entry.value;
          final isLast = idx == timeline.length - 1;

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Stepper Line & Circle
              Column(
                children: [
                  Container(
                    width: 22,
                    height: 22,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: item.isCompleted
                          ? AppTheme.primaryGreen
                          : (item.isCurrent ? AppTheme.warning : AppTheme.surface),
                      border: Border.all(
                        color: item.isCompleted
                            ? AppTheme.primaryGreen
                            : (item.isCurrent ? AppTheme.warning : AppTheme.border),
                        width: 2,
                      ),
                    ),
                    child: Center(
                      child: item.isCompleted
                          ? const Icon(Icons.check, size: 12, color: Colors.white)
                          : (item.isCurrent
                              ? Container(width: 6, height: 6, decoration: const BoxDecoration(shape: BoxShape.circle, color: Colors.white))
                              : null),
                    ),
                  ),
                  if (!isLast)
                    Container(
                      width: 2,
                      height: 28,
                      color: item.isCompleted ? AppTheme.primaryGreen.withValues(alpha: 0.5) : AppTheme.divider,
                    ),
                ],
              ),
              const SizedBox(width: 12),
              // Stage Information
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.label,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: item.isCurrent ? FontWeight.bold : FontWeight.w600,
                          color: item.isCompleted || item.isCurrent ? AppTheme.textPrimary : AppTheme.textMuted,
                        ),
                      ),
                      if (item.details != null && item.details!.isNotEmpty)
                        Text(
                          item.details!,
                          style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          );
        }).toList(),
      ),
    );
  }

  Widget _buildReceivingDiscrepancyCard() {
    final hasMismatch = _detail!.hasQuantityMismatch;

    return Container(
      padding: const EdgeInsets.all(AppTheme.space14),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: hasMismatch ? AppTheme.warning : AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildMetricItem('Expected Quantity', '${_detail!.expectedQuantity.toInt()} ${_detail!.quantityUnit}'),
              _buildMetricItem(
                'Received Quantity',
                _detail!.receivedQuantity != null ? '${_detail!.receivedQuantity!.toInt()} ${_detail!.quantityUnit}' : 'Pending Arrival',
                color: _detail!.receivedQuantity != null ? AppTheme.primaryDark : AppTheme.textSecondary,
              ),
              if (hasMismatch)
                _buildMetricItem(
                  'Difference',
                  '${_detail!.discrepancyAmount?.toInt() ?? 0} ${_detail!.quantityUnit}',
                  color: AppTheme.error,
                ),
            ],
          ),
          if (hasMismatch) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.warning.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, size: 16, color: Color(0xFFC05621)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${context.tr('quantity_mismatch')}: ${_detail!.discrepancyReason ?? "Reason not provided"}',
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFFC05621)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDistributionCard() {
    final received = _detail!.receivedQuantity ?? _detail!.quantity;
    final distributed = _detail!.distributedQuantity ?? 0.0;
    final remaining = _detail!.remainingQuantity ?? (received - distributed);

    return Container(
      padding: const EdgeInsets.all(AppTheme.space14),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _buildMetricItem('Intake Received', '${received.toInt()} meals'),
          _buildMetricItem('Distributed to Need', '${distributed.toInt()} meals', color: AppTheme.primaryGreen),
          _buildMetricItem('Remaining in Storage', '${remaining.toInt()} meals', color: remaining > 0 ? const Color(0xFFC05621) : AppTheme.textSecondary),
        ],
      ),
    );
  }

  Widget _buildParticipantsCard() {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space14),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: [
          _buildParticipantRow(
            icon: Icons.storefront_outlined,
            role: 'Donor',
            name: _detail!.donorName ?? 'Donor #${_detail!.donorId}',
            phone: _detail!.donorPhone,
          ),
          const Divider(height: 16, color: AppTheme.divider),
          _buildParticipantRow(
            icon: Icons.home_work_outlined,
            role: 'Receiving NGO',
            name: _detail!.ngoName ?? 'Awaiting NGO Acceptance',
            phone: null,
          ),
          const Divider(height: 16, color: AppTheme.divider),
          _buildParticipantRow(
            icon: Icons.directions_bike_outlined,
            role: 'Volunteer Courier',
            name: _detail!.volunteerName ?? 'Awaiting Courier Dispatch',
            phone: _detail!.volunteerPhone,
          ),
        ],
      ),
    );
  }

  Widget _buildParticipantRow({
    required IconData icon,
    required String role,
    required String name,
    String? phone,
  }) {
    return Row(
      children: [
        Icon(icon, size: 20, color: AppTheme.primaryDark),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(role, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
              Text(name, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
            ],
          ),
        ),
        if (phone != null && phone.isNotEmpty)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: AppTheme.border),
            ),
            child: Text(phone, style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary)),
          ),
      ],
    );
  }

  Widget _buildMetricItem(String label, String value, {Color? color}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary)),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            color: color ?? AppTheme.textPrimary,
          ),
        ),
      ],
    );
  }
}
