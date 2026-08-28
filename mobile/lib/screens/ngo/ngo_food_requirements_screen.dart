import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/ngo_provider.dart';
import '../../widgets/primary_action_button.dart';

/// Simple, effective NGO Demand & Requirements Editor with steppers.
class NgoFoodRequirementsScreen extends StatefulWidget {
  const NgoFoodRequirementsScreen({super.key});

  @override
  State<NgoFoodRequirementsScreen> createState() => _NgoFoodRequirementsScreenState();
}

class _NgoFoodRequirementsScreenState extends State<NgoFoodRequirementsScreen> {
  final Map<String, int> _demands = {
    'Rice': 100,
    'Bread': 50,
    'Fruits': 30,
    'Vegetables': 40,
    'Meals': 80,
  };

  final Map<String, Map<String, String>> _operatingHours = {
    'monday': {'open': '09:00', 'close': '21:00', 'status': 'open'},
    'tuesday': {'open': '09:00', 'close': '21:00', 'status': 'open'},
    'wednesday': {'open': '09:00', 'close': '21:00', 'status': 'open'},
    'thursday': {'open': '09:00', 'close': '21:00', 'status': 'open'},
    'friday': {'open': '09:00', 'close': '21:00', 'status': 'open'},
    'saturday': {'open': '10:00', 'close': '22:00', 'status': 'open'},
    'sunday': {'open': '10:00', 'close': '18:00', 'status': 'open'},
  };

  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ngoProv = Provider.of<NgoProvider>(context, listen: false);
      if (ngoProv.ngos.isNotEmpty) {
        final myNgo = ngoProv.ngos.first;
        if (myNgo.demandRequirements != null && myNgo.demandRequirements!.isNotEmpty) {
          setState(() {
            myNgo.demandRequirements!.forEach((k, v) {
              _demands[k] = (v as num).toInt();
            });
          });
        }
      }
    });
  }

  Future<void> _saveAll() async {
    setState(() => _isSaving = true);
    final ngoProv = Provider.of<NgoProvider>(context, listen: false);
    final ngoId = ngoProv.ngos.isNotEmpty ? ngoProv.ngos.first.id : 1;

    final okDemands = await ngoProv.updateDemands(ngoId, _demands);
    final okHours = await ngoProv.updateOperatingHours(ngoId, _operatingHours);

    if (mounted) {
      setState(() => _isSaving = false);
      if (okDemands && okHours) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ ${context.tr('confirm')}!'),
            backgroundColor: AppTheme.primaryGreen,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('food_category')),
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
            // ── Section 1: Demand Steppers ──────────────────────────────────
            Text(
              context.tr('food_category'),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: AppTheme.space16),

            ..._demands.entries.map((entry) {
              final cat = entry.key;
              final qty = entry.value;

              return Container(
                margin: const EdgeInsets.only(bottom: AppTheme.space12),
                padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space12),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      context.trFood(cat),
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                    Row(
                      children: [
                        IconButton(
                          onPressed: qty > 0 ? () => setState(() => _demands[cat] = qty - 10) : null,
                          icon: const Icon(Icons.remove_circle_outline, color: AppTheme.textSecondary),
                        ),
                        Container(
                          constraints: const BoxConstraints(minWidth: 50),
                          alignment: Alignment.center,
                          child: Text(
                            '$qty',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                          ),
                        ),
                        IconButton(
                          onPressed: () => setState(() => _demands[cat] = qty + 10),
                          icon: const Icon(Icons.add_circle_outline, color: AppTheme.primaryGreen),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: AppTheme.space24),

            // ── Section 2: Operating Schedule ───────────────────────────────
            Text(
              context.tr('role_ngo'),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: AppTheme.space16),

            ..._operatingHours.entries.map((entry) {
              final day = entry.key;
              final dayCap = '${day[0].toUpperCase()}${day.substring(1)}';
              final sched = entry.value;
              final isOpen = sched['status'] == 'open';

              return Container(
                margin: const EdgeInsets.only(bottom: AppTheme.space8),
                padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space8),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Row(
                  children: [
                    SizedBox(
                      width: 100,
                      child: Text(dayCap, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    ),
                    Expanded(
                      child: Text(
                        isOpen ? '${sched['open']} – ${sched['close']}' : 'Closed',
                        style: TextStyle(
                          fontSize: 13,
                          color: isOpen ? AppTheme.primaryGreen : AppTheme.error,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    Switch(
                      value: isOpen,
                      activeThumbColor: AppTheme.primaryGreen,
                      onChanged: (val) {
                        setState(() {
                          sched['status'] = val ? 'open' : 'closed';
                        });
                      },
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: AppTheme.space24),

            PrimaryActionButton(
              label: context.tr('confirm').toUpperCase(),
              icon: Icons.check_circle_outline,
              isLoading: _isSaving,
              onPressed: _saveAll,
            ),
            const SizedBox(height: AppTheme.space16),
          ],
        ),
      ),
    );
  }
}
