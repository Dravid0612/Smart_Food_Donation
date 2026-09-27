import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';
import '../../providers/volunteer_provider.dart';
import '../../widgets/availability_toggle.dart';

/// V5 Volunteer Vehicle Profile Screen.
/// Allows volunteers to configure their transit mode (Walking, Bike, Car, Van)
/// and operational carrying capacity.
class VolunteerVehicleProfileScreen extends StatefulWidget {
  const VolunteerVehicleProfileScreen({super.key});

  @override
  State<VolunteerVehicleProfileScreen> createState() => _VolunteerVehicleProfileScreenState();
}

class _VolunteerVehicleProfileScreenState extends State<VolunteerVehicleProfileScreen> {
  String _selectedVehicle = 'bike';
  int _capacity = 25;
  bool _isSaving = false;

  final List<Map<String, dynamic>> _vehicleOptions = [
    {
      'type': 'walking',
      'labelKey': 'vehicle_type_walking',
      'defaultCap': 15,
      'icon': Icons.directions_walk,
      'desc': 'Short-distance, local neighborhood rescues (< 1.5 km)',
    },
    {
      'type': 'bike',
      'labelKey': 'vehicle_type_bike',
      'defaultCap': 25,
      'icon': Icons.two_wheeler,
      'desc': 'Standard rapid rescue transit, dense traffic feasibility',
    },
    {
      'type': 'car',
      'labelKey': 'vehicle_type_car',
      'defaultCap': 60,
      'icon': Icons.directions_car,
      'desc': 'Medium-capacity meal rescue, cross-neighborhood transit',
    },
    {
      'type': 'van',
      'labelKey': 'vehicle_type_van',
      'defaultCap': 150,
      'icon': Icons.airport_shuttle,
      'desc': 'Large bulk surplus rescue, wedding halls & catered banquets',
    },
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final user = Provider.of<AuthProvider>(context, listen: false).currentUser;
      if (user != null) {
        setState(() {
          _selectedVehicle = user.vehicleType.toLowerCase();
          _capacity = user.carryingCapacity > 0 ? user.carryingCapacity : 25;
        });
      }
    });
  }

  void _onSelectVehicle(String type, int defaultCap) {
    setState(() {
      _selectedVehicle = type;
      _capacity = defaultCap;
    });
  }

  Future<void> _saveVehicleProfile() async {
    setState(() => _isSaving = true);
    final volProv = Provider.of<VolunteerProvider>(context, listen: false);
    final authProv = Provider.of<AuthProvider>(context, listen: false);

    final ok = await volProv.updateVehicleProfile(
      vehicleType: _selectedVehicle,
      carryingCapacity: _capacity,
    );

    if (!mounted) return;
    setState(() => _isSaving = false);

    if (ok) {
      await authProv.refreshUserProfile();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ ${context.tr('vehicle_updated_success')}'),
          backgroundColor: AppTheme.primaryGreen,
        ),
      );
      context.pop();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(context.trError('err_server')),
          backgroundColor: AppTheme.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(
          context.tr('vehicle_profile'),
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        actions: const [
          AvailabilityToggle(),
          SizedBox(width: 8),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTheme.space16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('vehicle_profile'),
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              context.tr('vehicle_profile_desc'),
              style: const TextStyle(
                fontSize: 13,
                color: AppTheme.textSecondary,
                height: 1.4,
              ),
            ),
            const SizedBox(height: AppTheme.space20),

            // Vehicle Option Cards
            ..._vehicleOptions.map((opt) {
              final isSelected = _selectedVehicle == opt['type'];
              final icon = opt['icon'] as IconData;
              final labelKey = opt['labelKey'] as String;
              final defaultCap = opt['defaultCap'] as int;
              final desc = opt['desc'] as String;

              return Container(
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                  color: AppTheme.card,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  border: Border.all(
                    color: isSelected ? AppTheme.primaryGreen : AppTheme.border,
                    width: isSelected ? 2 : 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: isSelected ? AppTheme.primaryGreen.withValues(alpha: 0.08) : Colors.black.withValues(alpha: 0.03),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: InkWell(
                  onTap: () => _onSelectVehicle(opt['type'] as String, defaultCap),
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  child: Padding(
                    padding: const EdgeInsets.all(AppTheme.space16),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: isSelected ? AppTheme.primaryGreen.withValues(alpha: 0.12) : Colors.grey.shade100,
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            icon,
                            color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
                            size: 26,
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Text(
                                    context.tr(labelKey),
                                    style: TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                      color: isSelected ? AppTheme.primaryGreen : AppTheme.textPrimary,
                                    ),
                                  ),
                                  const Spacer(),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                    decoration: BoxDecoration(
                                      color: isSelected ? AppTheme.primaryGreen.withValues(alpha: 0.1) : Colors.grey.shade100,
                                      borderRadius: BorderRadius.circular(AppTheme.radiusPill),
                                    ),
                                    child: Text(
                                      '~$defaultCap ${context.trUnit('Meals')}',
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                        color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                desc,
                                style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Icon(
                          isSelected ? Icons.radio_button_checked : Icons.radio_button_off,
                          color: isSelected ? AppTheme.primaryGreen : AppTheme.textSecondary,
                          size: 22,
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),

            const SizedBox(height: AppTheme.space16),

            // Stepper for Carrying Capacity Adjustment
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
                    context.tr('carrying_capacity'),
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${context.tr('carrying_capacity')} (${context.trUnit('Meals')})',
                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      IconButton.outlined(
                        icon: const Icon(Icons.remove),
                        onPressed: _capacity > 5
                            ? () => setState(() => _capacity = (_capacity - 5).clamp(5, 500))
                            : null,
                      ),
                      const SizedBox(width: 24),
                      Text(
                        '$_capacity',
                        style: const TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.w900,
                          color: AppTheme.primaryGreen,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        context.trUnit('Meals'),
                        style: const TextStyle(fontSize: 14, color: AppTheme.textSecondary, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(width: 24),
                      IconButton.outlined(
                        icon: const Icon(Icons.add),
                        onPressed: _capacity < 500
                            ? () => setState(() => _capacity = (_capacity + 5).clamp(5, 500))
                            : null,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppTheme.space24),

            // Save CTA Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isSaving ? null : _saveVehicleProfile,
                icon: _isSaving
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.save_outlined, color: Colors.white),
                label: Text(
                  context.tr('save').toUpperCase(),
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryGreen,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
                  elevation: 2,
                ),
              ),
            ),
            const SizedBox(height: AppTheme.space32),
          ],
        ),
      ),
    );
  }
}
