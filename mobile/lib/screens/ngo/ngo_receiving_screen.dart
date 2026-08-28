import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/donation_provider.dart';
import '../../widgets/primary_action_button.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/report_problem_dialog.dart';

/// NGO Screen to verify receipt of delivered food batch.
class NgoReceivingScreen extends StatefulWidget {
  final int donationId;
  const NgoReceivingScreen({super.key, required this.donationId});

  @override
  State<NgoReceivingScreen> createState() => _NgoReceivingScreenState();
}

class _NgoReceivingScreenState extends State<NgoReceivingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _quantityReceivedController = TextEditingController();
  final _notesController = TextEditingController();
  String _conditionOnArrival = 'Good';
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final prov = Provider.of<DonationProvider>(context, listen: false);
      prov.fetchDonationDetail(widget.donationId).then((_) {
        if (prov.currentDetail != null) {
          _quantityReceivedController.text = prov.currentDetail!.quantity.toInt().toString();
        }
      });
    });
  }

  @override
  void dispose() {
    _quantityReceivedController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _confirmDelivery() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSubmitting = true);

    final prov = Provider.of<DonationProvider>(context, listen: false);
    final ok = await prov.deliverDonation(widget.donationId);

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ ${context.tr('status_delivered')}'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
      context.pushReplacement('/ngo/distribution/${widget.donationId}');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(prov.errorMessage != null ? context.trError(prov.errorMessage!) : context.trError('err_server')),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final prov = Provider.of<DonationProvider>(context);
    final item = prov.currentDetail;

    if (prov.isLoading || item == null) {
      return Scaffold(
        appBar: AppBar(title: Text(context.tr('confirm'))),
        body: LoadingStateWidget(message: context.tr('processing')),
      );
    }

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('confirm')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTheme.space16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Summary card
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
                      context.trFood(item.foodName),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.textPrimary),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${item.quantity.toInt()} ${context.trUnit(item.quantityUnit)} • ${context.trCategory(item.foodCategory)}',
                      style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Icon(Icons.two_wheeler, size: 16, color: AppTheme.textSecondary),
                        const SizedBox(width: 4),
                        Text(
                          '${context.tr('assigned_volunteer')}: ${item.volunteerName ?? context.tr('role_volunteer')}',
                          style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppTheme.space20),

              Text(
                context.tr('rescue_live_tracking'),
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
              ),
              const SizedBox(height: AppTheme.space16),

              TextFormField(
                controller: _quantityReceivedController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: context.tr('quantity'),
                  hintText: '${item.quantity.toInt()} ${context.trUnit(item.quantityUnit)}',
                  prefixIcon: const Icon(Icons.inventory_2_outlined),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return context.tr('field_required');
                  final n = double.tryParse(v);
                  if (n == null || n <= 0) return context.tr('field_required');
                  return null;
                },
              ),
              const SizedBox(height: AppTheme.space16),

              Text(context.tr('visual_condition'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              const SizedBox(height: AppTheme.space8),
              Row(
                children: ['Good', 'Fair', 'Poor'].map((c) {
                  final isSelected = _conditionOnArrival == c;
                  return Padding(
                    padding: const EdgeInsets.only(right: AppTheme.space8),
                    child: ChoiceChip(
                      label: Text(context.trVisual(c)),
                      selected: isSelected,
                      selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.15),
                      backgroundColor: AppTheme.card,
                      side: BorderSide(color: isSelected ? AppTheme.primaryGreen : AppTheme.border),
                      labelStyle: TextStyle(
                        color: isSelected ? AppTheme.primaryGreen : AppTheme.textPrimary,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      ),
                      onSelected: (_) => setState(() => _conditionOnArrival = c),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: AppTheme.space16),

              TextFormField(
                controller: _notesController,
                maxLines: 2,
                decoration: InputDecoration(
                  labelText: context.tr('rating_feedback_hint'),
                ),
              ),
              const SizedBox(height: AppTheme.space28),

              PrimaryActionButton(
                label: context.tr('confirm').toUpperCase(),
                icon: Icons.task_alt,
                isLoading: _isSubmitting,
                onPressed: _confirmDelivery,
              ),
              const SizedBox(height: AppTheme.space12),
              Center(
                child: TextButton.icon(
                  onPressed: () {
                    showDialog(
                      context: context,
                      builder: (ctx) => ReportProblemDialog(
                        donationId: widget.donationId,
                        currentRole: 'ngo',
                        initialFoodConditionConcern: true,
                      ),
                    );
                  },
                  icon: const Icon(Icons.warning_amber_rounded, size: 16, color: AppTheme.error),
                  label: Text(
                    context.tr('food_condition_concern'),
                    style: const TextStyle(fontSize: 12, color: AppTheme.error, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
