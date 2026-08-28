import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/primary_action_button.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/rescue_feedback_card.dart';

/// NGO Screen for recording meal distribution to beneficiaries.
class NgoDistributionScreen extends StatefulWidget {
  final int donationId;
  const NgoDistributionScreen({super.key, required this.donationId});

  @override
  State<NgoDistributionScreen> createState() => _NgoDistributionScreenState();
}

class _NgoDistributionScreenState extends State<NgoDistributionScreen> {
  final _distributedController = TextEditingController();
  final _locationController = TextEditingController();
  final _beneficiariesController = TextEditingController();
  bool _isSubmitting = false;

  final List<Map<String, dynamic>> _distributions = [];
  int _totalReceived = 80;
  int _totalDistributed = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final prov = Provider.of<DonationProvider>(context, listen: false);
      prov.fetchDonationDetail(widget.donationId).then((_) {
        if (prov.currentDetail != null && mounted) {
          setState(() => _totalReceived = prov.currentDetail!.quantity.toInt());
        }
      });
    });
  }

  @override
  void dispose() {
    _distributedController.dispose();
    _locationController.dispose();
    _beneficiariesController.dispose();
    super.dispose();
  }

  Future<void> _recordDistribution() async {
    final qty = int.tryParse(_distributedController.text.trim()) ?? 0;
    if (qty <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('field_required')), backgroundColor: AppTheme.error),
      );
      return;
    }
    final remaining = _totalReceived - _totalDistributed;
    if (qty > remaining) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${context.tr('remaining_time')}: $remaining'),
          backgroundColor: AppTheme.error,
        ),
      );
      return;
    }

    final beneficiaries = int.tryParse(_beneficiariesController.text.trim()) ?? qty;
    final location = _locationController.text.trim().isEmpty ? 'Community Shelter' : _locationController.text.trim();

    setState(() => _isSubmitting = true);
    final prov = Provider.of<DonationProvider>(context, listen: false);
    final ok = await prov.recordDistribution(
      donationId: widget.donationId,
      distributedQuantity: (_totalDistributed + qty).toDouble(),
      receivedQuantity: _totalReceived.toDouble(),
      remainingQuantity: (remaining - qty).toDouble(),
      beneficiariesServed: beneficiaries,
      remarks: 'Distributed at $location',
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (ok) {
      setState(() {
        _distributions.add({
          'qty': qty,
          'location': location,
          'beneficiaries': beneficiaries,
          'time': DateTime.now(),
        });
        _totalDistributed += qty;
        _distributedController.clear();
        _locationController.clear();
        _beneficiariesController.clear();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ $qty ${context.trUnit('Meals')} ${context.tr('status_completed')}!'),
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
    final remaining = _totalReceived - _totalDistributed;
    final progress = _totalReceived > 0 ? _totalDistributed / _totalReceived : 0.0;

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('distribute_meals')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: prov.isLoading
          ? LoadingStateWidget(message: context.tr('processing'))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(AppTheme.space16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Progress Card
                  Container(
                    padding: const EdgeInsets.all(AppTheme.space20),
                    decoration: BoxDecoration(
                      color: AppTheme.card,
                      borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                      border: Border.all(color: AppTheme.border),
                      boxShadow: AppTheme.shadowCard,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.tr('distribution_summary'),
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary, letterSpacing: -0.2),
                        ),
                        const SizedBox(height: AppTheme.space16),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            _statBlock('$_totalReceived', context.tr('meals_received'), AppTheme.textPrimary),
                            Container(width: 1, height: 36, color: AppTheme.divider),
                            _statBlock('$_totalDistributed', context.tr('meals_distributed'), AppTheme.primaryGreen),
                            Container(width: 1, height: 36, color: AppTheme.divider),
                            _statBlock('$remaining', context.tr('meals_remaining'), remaining > 0 ? AppTheme.secondaryTerracotta : AppTheme.textSecondary),
                          ],
                        ),
                        const SizedBox(height: AppTheme.space16),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                          child: LinearProgressIndicator(
                            value: progress.clamp(0.0, 1.0),
                            backgroundColor: AppTheme.background,
                            valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.primaryGreen),
                            minHeight: 8,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppTheme.space24),

                  Text(context.tr('distribute_meals'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppTheme.textPrimary)),
                  const SizedBox(height: AppTheme.space16),

                  TextFormField(
                    controller: _distributedController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: context.tr('quantity'),
                      hintText: '${context.tr('remaining_time')}: $remaining',
                      prefixIcon: const Icon(Icons.restaurant_outlined),
                    ),
                  ),
                  const SizedBox(height: AppTheme.space12),

                  TextFormField(
                    controller: _locationController,
                    decoration: InputDecoration(
                      labelText: context.tr('pickup_address'),
                      prefixIcon: const Icon(Icons.location_on_outlined),
                    ),
                  ),
                  const SizedBox(height: AppTheme.space24),

                  PrimaryActionButton(
                    label: context.tr('distribute_meals').toUpperCase(),
                    icon: Icons.check_circle_outline,
                    isLoading: _isSubmitting,
                    onPressed: remaining == 0 ? null : _recordDistribution,
                  ),
                  const SizedBox(height: AppTheme.space16),

                  // Rescue Feedback & Rating
                  RescueFeedbackCard(
                    donationId: widget.donationId,
                    currentRole: 'ngo',
                  ),
                ],
              ),
            ),
    );
  }

  Widget _statBlock(String value, String label, Color color) {
    return Column(
      children: [
        Text(value, style: TextStyle(color: color, fontSize: 24, fontWeight: FontWeight.bold)),
        const SizedBox(height: 2),
        Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11), textAlign: TextAlign.center),
      ],
    );
  }
}
