import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/ngo_provider.dart';
import '../../widgets/primary_action_button.dart';
import '../../widgets/role_bottom_nav.dart';

/// NGO Requirements Screen managing:
/// 1. Intake Capacity & Availability
/// 2. Food Demand by Category
/// 3. Weekly Operating Hours
class NgoFoodRequirementsScreen extends StatefulWidget {
  const NgoFoodRequirementsScreen({super.key});

  @override
  State<NgoFoodRequirementsScreen> createState() => _NgoFoodRequirementsScreenState();
}

class _NgoFoodRequirementsScreenState extends State<NgoFoodRequirementsScreen> {
  int _capacity = 150;
  bool _isAvailable = true;

  final Map<String, int> _demands = {
    'Cooked Food': 80,
    'Bakery': 30,
    'Fruits': 25,
    'Vegetables': 35,
    'Packaged Food': 40,
  };

  final Map<String, Map<String, String>> _operatingHours = {
    'monday': {'open': '08:00', 'close': '20:00', 'status': 'open'},
    'tuesday': {'open': '08:00', 'close': '20:00', 'status': 'open'},
    'wednesday': {'open': '08:00', 'close': '20:00', 'status': 'open'},
    'thursday': {'open': '08:00', 'close': '20:00', 'status': 'open'},
    'friday': {'open': '08:00', 'close': '20:00', 'status': 'open'},
    'saturday': {'open': '09:00', 'close': '21:00', 'status': 'open'},
    'sunday': {'open': '09:00', 'close': '18:00', 'status': 'open'},
  };

  bool _isSaving = false;
  bool _showReminder = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadInitialData();
    });
  }

  void _loadInitialData() {
    final ngoProv = Provider.of<NgoProvider>(context, listen: false);
    final myNgo = ngoProv.myNgo ?? (ngoProv.ngos.isNotEmpty ? ngoProv.ngos.first : null);
    if (myNgo != null) {
      setState(() {
        _capacity = myNgo.capacity;
        _isAvailable = myNgo.isAvailable;
        if (myNgo.demandRequirements != null && myNgo.demandRequirements!.isNotEmpty) {
          myNgo.demandRequirements!.forEach((k, v) {
            _demands[k] = (v as num).toInt();
          });
        }
        if (myNgo.operatingHours != null && myNgo.operatingHours!.isNotEmpty) {
          myNgo.operatingHours!.forEach((day, val) {
            if (val is Map) {
              _operatingHours[day] = {
                'open': val['open']?.toString() ?? '08:00',
                'close': val['close']?.toString() ?? '20:00',
                'status': (val['closed'] == true || val['status'] == 'closed') ? 'closed' : 'open',
              };
            }
          });
        }
      });
    }
  }

  Future<void> _saveAll() async {
    setState(() => _isSaving = true);
    final ngoProv = Provider.of<NgoProvider>(context, listen: false);
    final myNgo = ngoProv.myNgo ?? (ngoProv.ngos.isNotEmpty ? ngoProv.ngos.first : null);
    final ngoId = myNgo?.id ?? 1;

    final okCapacity = await ngoProv.updateNgoCapacity(ngoId, _capacity, _isAvailable);
    final okDemands = await ngoProv.updateDemands(ngoId, _demands);
    final okHours = await ngoProv.updateOperatingHours(ngoId, _operatingHours);

    if (mounted) {
      setState(() => _isSaving = false);
      if (okCapacity && okDemands && okHours) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ ${context.tr('confirm')}!'),
            backgroundColor: AppTheme.primaryGreen,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.trError('err_server')),
            backgroundColor: AppTheme.error,
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
        title: Text(
          context.tr('nav_requirements'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTheme.space16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Persistent Requirements Informational Reminder ───────────────
            if (_showReminder)
              Container(
                margin: const EdgeInsets.only(bottom: AppTheme.space16),
                padding: const EdgeInsets.all(AppTheme.space14),
                decoration: BoxDecoration(
                  color: AppTheme.info.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(color: AppTheme.info.withValues(alpha: 0.3)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.schedule, color: AppTheme.info, size: 20),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.tr('requirements_reminder_title'),
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.info),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            context.tr('requirements_reminder_desc'),
                            style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: () => setState(() => _showReminder = false),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: Text(
                        context.tr('dismiss_reminder'),
                        style: const TextStyle(fontSize: 12, color: AppTheme.info, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),

            // ── Section 1: Capacity & Availability ──────────────────────────
            Container(
              padding: const EdgeInsets.all(AppTheme.space16),
              decoration: BoxDecoration(
                color: AppTheme.card,
                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                border: Border.all(color: AppTheme.border),
                boxShadow: AppTheme.shadowCard,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.tr('intake_capacity'),
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${context.tr('unit_meals')} / day',
                            style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                          ),
                        ],
                      ),
                      Row(
                        children: [
                          IconButton(
                            onPressed: _capacity > 25 ? () => setState(() => _capacity -= 25) : null,
                            icon: const Icon(Icons.remove_circle_outline, color: AppTheme.textSecondary),
                          ),
                          Container(
                            constraints: const BoxConstraints(minWidth: 50),
                            alignment: Alignment.center,
                            child: Text(
                              '$_capacity',
                              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryGreen),
                            ),
                          ),
                          IconButton(
                            onPressed: () => setState(() => _capacity += 25),
                            icon: const Icon(Icons.add_circle_outline, color: AppTheme.primaryGreen),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.tr('available'),
                            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _isAvailable ? 'Currently receiving rescues' : 'Temporarily paused',
                            style: TextStyle(
                              fontSize: 12,
                              color: _isAvailable ? AppTheme.primaryGreen : AppTheme.error,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                      Switch(
                        value: _isAvailable,
                        activeThumbColor: AppTheme.primaryGreen,
                        onChanged: (val) => setState(() => _isAvailable = val),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppTheme.space20),

            // ── Section 2: Demand Steppers ──────────────────────────────────
            Text(
              context.tr('food_category'),
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: AppTheme.space12),

            ..._demands.entries.map((entry) {
              final cat = entry.key;
              final qty = entry.value;

              return Container(
                margin: const EdgeInsets.only(bottom: AppTheme.space10),
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
            const SizedBox(height: AppTheme.space20),

            // ── Section 3: Operating Schedule ───────────────────────────────
            Text(
              context.tr('operating_hours'),
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
            ),
            const SizedBox(height: AppTheme.space12),

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
      bottomNavigationBar: const RoleBottomNav(currentRole: 'ngo', currentIndex: 1),
    );
  }
}
