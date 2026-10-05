import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/error_state_widget.dart';
import '../../widgets/donation_status_timeline.dart';
import '../../models/donation_model.dart';

/// Combined N5 Operational Screen for NGO Receiving and Meal Distribution.
/// Distinguishes DONATED (expected), RECEIVED, and DISTRIBUTED quantities.
class NgoReceivingDistributionScreen extends StatefulWidget {
  final int donationId;
  final DonationModel? donation;
  const NgoReceivingDistributionScreen({
    super.key,
    required this.donationId,
    this.donation,
  });

  @override
  State<NgoReceivingDistributionScreen> createState() => _NgoReceivingDistributionScreenState();
}

class _NgoReceivingDistributionScreenState extends State<NgoReceivingDistributionScreen> {
  final _receiptFormKey = GlobalKey<FormState>();
  final _distFormKey = GlobalKey<FormState>();

  final _receivedQtyController = TextEditingController();
  final _receiptNotesController = TextEditingController();
  final _distributeQtyController = TextEditingController();
  final _locationController = TextEditingController();
  final _beneficiariesController = TextEditingController();

  String _conditionOnArrival = 'Good';
  bool _isConfirmingReceipt = false;
  bool _isLoggingDist = false;

  final List<Map<String, dynamic>> _distributionEntries = [];
  double _expectedQty = 0;
  double _receivedQty = 0;
  double _totalDistributed = 0;

  @override
  void initState() {
    super.initState();
    if (widget.donation != null) {
      _expectedQty = widget.donation!.quantity;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadDonation();
    });
  }

  @override
  void dispose() {
    _receivedQtyController.dispose();
    _receiptNotesController.dispose();
    _distributeQtyController.dispose();
    _locationController.dispose();
    _beneficiariesController.dispose();
    super.dispose();
  }

  Future<void> _loadDonation() async {
    if (widget.donation != null) {
      final detail = widget.donation!;
      if (mounted) {
        setState(() {
          _expectedQty = detail.quantity;
          _receivedQty = detail.quantity;
          _receivedQtyController.text = detail.quantity.toInt().toString();
        });
      }
      return;
    }
    final prov = Provider.of<DonationProvider>(context, listen: false);
    await prov.fetchDonationDetail(widget.donationId);
    if (prov.currentDetail != null && mounted) {
      final detail = prov.currentDetail!;
      setState(() {
        _expectedQty = detail.quantity;
        // If already delivered, initialize receivedQty to donation quantity or existing value
        final isDelivered = ['delivered', 'completed'].contains(detail.status.toLowerCase());
        if (isDelivered) {
          _receivedQty = detail.quantity;
          _receivedQtyController.text = _receivedQty.toInt().toString();
        } else {
          _receivedQtyController.text = _expectedQty.toInt().toString();
        }
      });
    }
  }

  Future<void> _confirmReceipt() async {
    if (!_receiptFormKey.currentState!.validate()) return;
    final parsedQty = double.tryParse(_receivedQtyController.text.trim()) ?? _expectedQty;

    setState(() => _isConfirmingReceipt = true);
    final prov = Provider.of<DonationProvider>(context, listen: false);
    final ok = await prov.deliverDonation(
      widget.donationId,
      receivedQuantity: parsedQty,
      condition: _conditionOnArrival,
      remarks: _receiptNotesController.text.trim().isNotEmpty ? _receiptNotesController.text.trim() : null,
    );

    if (!mounted) return;
    setState(() => _isConfirmingReceipt = false);

    if (ok) {
      setState(() {
        _receivedQty = parsedQty;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ ${context.tr('receipt_confirmed_success')}'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
      _loadDonation();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(prov.errorMessage != null ? context.trError(prov.errorMessage!) : context.trError('err_server')),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  Future<void> _logDistribution() async {
    if (!_distFormKey.currentState!.validate()) return;

    final qty = double.tryParse(_distributeQtyController.text.trim()) ?? 0;
    if (qty <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('field_required')), backgroundColor: AppTheme.error),
      );
      return;
    }

    final remaining = _receivedQty - _totalDistributed;
    if (qty > remaining) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${context.tr('remaining_qty')}: ${remaining.toInt()}'),
          backgroundColor: AppTheme.error,
        ),
      );
      return;
    }

    final beneficiaries = int.tryParse(_beneficiariesController.text.trim()) ?? qty.toInt();
    final location = _locationController.text.trim().isEmpty ? 'Community Center' : _locationController.text.trim();

    setState(() => _isLoggingDist = true);
    final prov = Provider.of<DonationProvider>(context, listen: false);
    final ok = await prov.recordDistribution(
      donationId: widget.donationId,
      distributedQuantity: _totalDistributed + qty,
      receivedQuantity: _receivedQty,
      remainingQuantity: remaining - qty,
      beneficiariesServed: beneficiaries,
      remarks: 'Distributed at $location',
    );

    if (!mounted) return;
    setState(() => _isLoggingDist = false);

    if (ok) {
      setState(() {
        _distributionEntries.add({
          'qty': qty.toInt(),
          'location': location,
          'beneficiaries': beneficiaries,
          'time': DateTime.now(),
        });
        _totalDistributed += qty;
        _distributeQtyController.clear();
        _locationController.clear();
        _beneficiariesController.clear();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ ${context.tr('distribution_logged_success')}'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.trError(prov.errorMessage ?? 'err_server')),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final detail = widget.donation ?? prov.currentDetail;

    if (prov.isLoading && detail == null) {
      return Scaffold(
        appBar: AppBar(title: Text(context.tr('receiving_and_distribution'))),
        body: LoadingStateWidget(message: context.tr('loading')),
      );
    }

    if (detail == null) {
      return Scaffold(
        appBar: AppBar(title: Text(context.tr('receiving_and_distribution'))),
        body: ErrorStateWidget(
          message: prov.errorMessage ?? context.tr('err_not_found'),
          onRetry: _loadDonation,
        ),
      );
    }

    final isDelivered = ['delivered', 'completed'].contains(detail.status.toLowerCase());
    final effectiveReceived = _receivedQty > 0 ? _receivedQty : (isDelivered ? _expectedQty : 0.0);
    final remainingMeals = (effectiveReceived - _totalDistributed).clamp(0.0, 99999.0);

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(
          context.tr('receiving_and_distribution'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTheme.space16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Operational Metric Summary Cards ─────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppTheme.space16),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                border: Border.all(color: AppTheme.border),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.inventory_2_outlined, color: AppTheme.primaryGreen, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        detail.foodName,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: isDelivered ? AppTheme.primaryGreen.withValues(alpha: 0.1) : AppTheme.urgentAmber.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                        ),
                        child: Text(
                          context.trStatus(detail.status),
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: isDelivered ? AppTheme.primaryGreen : AppTheme.urgentAmber,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppTheme.space16),
                  const Divider(height: 1),
                  const SizedBox(height: AppTheme.space16),

                  // 4 Distinct Metric Tiles: DONATED | RECEIVED | DISTRIBUTED | REMAINING
                  Row(
                    children: [
                      _buildMetricTile(
                        label: context.tr('expected_qty'),
                        value: '${detail.quantity.toInt()}',
                        unit: context.trUnit(detail.quantityUnit),
                        color: AppTheme.textPrimary,
                        bgColor: Colors.grey.shade100,
                      ),
                      const SizedBox(width: 8),
                      _buildMetricTile(
                        label: context.tr('received_qty'),
                        value: effectiveReceived > 0 ? '${effectiveReceived.toInt()}' : '—',
                        unit: context.trUnit(detail.quantityUnit),
                        color: AppTheme.primaryGreen,
                        bgColor: AppTheme.primaryGreen.withValues(alpha: 0.08),
                      ),
                      const SizedBox(width: 8),
                      _buildMetricTile(
                        label: context.tr('distributed_qty'),
                        value: '${_totalDistributed.toInt()}',
                        unit: context.trUnit(detail.quantityUnit),
                        color: AppTheme.trustTeal,
                        bgColor: AppTheme.trustTeal.withValues(alpha: 0.08),
                      ),
                      const SizedBox(width: 8),
                      _buildMetricTile(
                        label: context.tr('remaining_qty'),
                        value: effectiveReceived > 0 ? '${remainingMeals.toInt()}' : '—',
                        unit: context.trUnit(detail.quantityUnit),
                        color: remainingMeals > 0 ? AppTheme.urgentAmber : AppTheme.textSecondary,
                        bgColor: AppTheme.urgentAmber.withValues(alpha: 0.08),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppTheme.space16),

            // ── Shared Timeline ─────────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppTheme.space16),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                border: Border.all(color: AppTheme.border),
              ),
              child: DonationStatusTimeline(
                status: detail.status,
                pickupMode: detail.pickupMode,
              ),
            ),
            const SizedBox(height: AppTheme.space20),

            // ── Action 1: CONFIRM RECEIPT ───────────────────────────────────
            Container(
              padding: const EdgeInsets.all(AppTheme.space16),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                border: Border.all(
                  color: isDelivered ? AppTheme.primaryGreen.withValues(alpha: 0.4) : AppTheme.border,
                ),
              ),
              child: Form(
                key: _receiptFormKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          isDelivered ? Icons.check_circle : Icons.inventory,
                          color: isDelivered ? AppTheme.primaryGreen : AppTheme.urgentAmber,
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          isDelivered
                              ? '1. ${context.tr('confirm_receipt')} (✓ ${context.tr('status_delivered')})'
                              : '1. ${context.tr('confirm_receipt')}',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: isDelivered ? AppTheme.primaryGreen : AppTheme.textPrimary,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (isDelivered) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryGreen.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.verified, color: AppTheme.primaryGreen, size: 20),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                '${context.tr('received_qty')}: ${effectiveReceived.toInt()} ${context.trUnit(detail.quantityUnit)} • ${context.tr('condition_on_arrival')}: $_conditionOnArrival',
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.primaryGreen),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ] else ...[
                      TextFormField(
                        controller: _receivedQtyController,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: '${context.tr('received_qty')} (${context.trUnit(detail.quantityUnit)})',
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.radiusInput)),
                          prefixIcon: const Icon(Icons.scale_outlined),
                        ),
                        validator: (val) {
                          if (val == null || val.trim().isEmpty) return context.tr('field_required');
                          final n = double.tryParse(val.trim());
                          if (n == null || n <= 0) return context.tr('field_required');
                          return null;
                        },
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        initialValue: _conditionOnArrival,
                        decoration: InputDecoration(
                          labelText: context.tr('condition_on_arrival'),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.radiusInput)),
                          prefixIcon: const Icon(Icons.health_and_safety_outlined),
                        ),
                        items: ['Good', 'Adequate', 'Fair'].map((c) {
                          return DropdownMenuItem(value: c, child: Text(c));
                        }).toList(),
                        onChanged: (val) {
                          if (val != null) setState(() => _conditionOnArrival = val);
                        },
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _receiptNotesController,
                        decoration: InputDecoration(
                          labelText: 'Arrival Notes / Condition Remarks (Optional)',
                          hintText: 'e.g. Received intact, temperature checked, no spillage',
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.radiusInput)),
                          prefixIcon: const Icon(Icons.note_alt_outlined),
                        ),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: _isConfirmingReceipt ? null : _confirmReceipt,
                          icon: _isConfirmingReceipt
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.check_circle_outline, color: Colors.white),
                          label: Text(
                            context.tr('confirm_receipt').toUpperCase(),
                            style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 0.5),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryGreen,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: AppTheme.space20),

            // ── Action 2: LOG BENEFICIARY DISTRIBUTION ──────────────────────
            Container(
              padding: const EdgeInsets.all(AppTheme.space16),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                border: Border.all(color: AppTheme.border),
              ),
              child: Form(
                key: _distFormKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.volunteer_activism, color: AppTheme.trustTeal, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          '2. ${context.tr('log_distribution')}',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      context.tr('receiving_distribution_subtitle'),
                      style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                    ),
                    const SizedBox(height: 14),
                    if (!isDelivered && _receivedQty == 0) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.amber.shade50,
                          borderRadius: BorderRadius.circular(AppTheme.radiusInput),
                          border: Border.all(color: Colors.amber.shade200),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.info_outline, color: AppTheme.urgentAmber, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '${context.tr('confirm_receipt')} first before logging distribution.',
                                style: TextStyle(fontSize: 12, color: Colors.amber.shade900),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ] else ...[
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _distributeQtyController,
                              keyboardType: TextInputType.number,
                              decoration: InputDecoration(
                                labelText: '${context.tr('distributed_qty')} (${context.trUnit(detail.quantityUnit)})',
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.radiusInput)),
                                prefixIcon: const Icon(Icons.food_bank_outlined),
                              ),
                              validator: (val) {
                                if (val == null || val.trim().isEmpty) return context.tr('field_required');
                                final n = double.tryParse(val.trim());
                                if (n == null || n <= 0) return context.tr('field_required');
                                return null;
                              },
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextFormField(
                              controller: _beneficiariesController,
                              keyboardType: TextInputType.number,
                              decoration: InputDecoration(
                                labelText: context.tr('beneficiaries_served'),
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.radiusInput)),
                                prefixIcon: const Icon(Icons.people_outline),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _locationController,
                        decoration: InputDecoration(
                          labelText: context.tr('distribution_location'),
                          hintText: 'e.g. Community Shelter, Anna Nagar',
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppTheme.radiusInput)),
                          prefixIcon: const Icon(Icons.place_outlined),
                        ),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: (_isLoggingDist || remainingMeals <= 0) ? null : _logDistribution,
                          icon: _isLoggingDist
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.send_outlined, color: Colors.white),
                          label: Text(
                            context.tr('log_distribution').toUpperCase(),
                            style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 0.5),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.trustTeal,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: AppTheme.space20),

            // ── Section 3: Distribution Entries List ─────────────────────────
            Text(
              context.tr('distribution_entries'),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 10),
            if (_distributionEntries.isEmpty) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppTheme.space24),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Center(
                  child: Column(
                    children: [
                      const Icon(Icons.receipt_long_outlined, size: 36, color: AppTheme.textSecondary),
                      const SizedBox(height: 8),
                      Text(
                        context.tr('no_available_donations'),
                        style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                      ),
                    ],
                  ),
                ),
              ),
            ] else ...[
              ..._distributionEntries.map((entry) {
                final dt = entry['time'] as DateTime;
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(AppTheme.space12),
                  decoration: BoxDecoration(
                    color: AppTheme.card,
                    borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppTheme.trustTeal.withValues(alpha: 0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.check, color: AppTheme.trustTeal, size: 16),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${entry['qty']} ${context.trUnit(detail.quantityUnit)} • ${entry['location']}',
                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '${context.tr('beneficiaries_served')}: ${entry['beneficiaries']} • ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}',
                              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
            const SizedBox(height: AppTheme.space16),
            Container(
              padding: const EdgeInsets.all(AppTheme.space12),
              decoration: BoxDecoration(
                color: AppTheme.surfaceWarm,
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
                      context.tr('tax_deduction_disclaimer'),
                      style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppTheme.space32),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricTile({
    required String label,
    required String value,
    required String unit,
    required Color color,
    required Color bgColor,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        ),
        child: Column(
          children: [
            Text(
              label.toUpperCase(),
              style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: color.withValues(alpha: 0.8), letterSpacing: 0.3),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: color),
            ),
            Text(
              unit,
              style: TextStyle(fontSize: 10, color: color.withValues(alpha: 0.7)),
            ),
          ],
        ),
      ),
    );
  }
}
