import 'package:flutter/material.dart';
import '../core/utils/food_rescue_status_helper.dart';

class UrgencyChip extends StatelessWidget {
  final String urgency;
  final int? remainingMinutes;

  const UrgencyChip({
    super.key,
    required this.urgency,
    this.remainingMinutes,
  });

  @override
  Widget build(BuildContext context) {
    final info = FoodRescueStatusHelper.getRescueUrgency(
      context,
      urgency,
      remainingMinutes: remainingMinutes,
    );

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: info.backgroundColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: info.borderColor, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(info.icon, size: 14, color: info.color),
          const SizedBox(width: 4),
          Text(
            info.label,
            style: TextStyle(
              color: info.color,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
