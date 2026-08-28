import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';

/// Card showing volunteer vehicle type and carrying capacity constraint.
class VehicleCapacityCard extends StatelessWidget {
  final String vehicleType;
  final int capacity;
  final VoidCallback? onEdit;

  const VehicleCapacityCard({
    super.key,
    required this.vehicleType,
    required this.capacity,
    this.onEdit,
  });

  IconData _getVehicleIcon(String type) {
    switch (type.toLowerCase()) {
      case 'bike':
      case 'motorcycle':
        return Icons.two_wheeler;
      case 'car':
        return Icons.directions_car;
      case 'van':
      case 'truck':
        return Icons.local_shipping;
      case 'walking':
      default:
        return Icons.directions_walk;
    }
  }

  @override
  Widget build(BuildContext context) {
    final icon = _getVehicleIcon(vehicleType);

    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(AppTheme.space12),
            decoration: BoxDecoration(
              color: AppTheme.primaryGreen.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
            ),
            child: Icon(icon, color: AppTheme.primaryGreen, size: 28),
          ),
          const SizedBox(width: AppTheme.space16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${context.tr('vehicle_type')}: ${(vehicleType.isNotEmpty ? vehicleType[0].toUpperCase() + vehicleType.substring(1) : "Bike")}',
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '${context.tr('payload_capacity')}: $capacity ${context.tr('unit_meals')}',
                  style: const TextStyle(
                    fontSize: 13,
                    color: AppTheme.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          if (onEdit != null)
            IconButton(
              icon: const Icon(Icons.edit_outlined, size: 20, color: AppTheme.textSecondary),
              onPressed: onEdit,
            ),
        ],
      ),
    );
  }
}
