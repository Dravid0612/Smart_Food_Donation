import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../models/performance_model.dart';

class WhyThisMatchDialog extends StatelessWidget {
  final String title;
  final String participantName;
  final String role;
  final double score;
  final List<MatchReasonItem> reasons;
  final double? distanceKm;
  final int? etaMinutes;

  const WhyThisMatchDialog({
    super.key,
    required this.title,
    required this.participantName,
    required this.role,
    required this.score,
    required this.reasons,
    this.distanceKm,
    this.etaMinutes,
  });

  static void show(
    BuildContext context, {
    required String title,
    required String participantName,
    required String role,
    required double score,
    required List<MatchReasonItem> reasons,
    double? distanceKm,
    int? etaMinutes,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => WhyThisMatchDialog(
        title: title,
        participantName: participantName,
        role: role,
        score: score,
        reasons: reasons,
        distanceKm: distanceKm,
        etaMinutes: etaMinutes,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        top: 20,
        left: 20,
        right: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Drag Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Title & Match Badge
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title.isNotEmpty ? title : context.tr('why_this_match'),
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    participantName,
                    style: TextStyle(
                      color: Colors.grey.shade700,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.green.shade300),
                ),
                child: Row(
                  children: [
                    Icon(Icons.bolt, color: Colors.green.shade700, size: 16),
                    const SizedBox(width: 4),
                    Text(
                      '${score.toStringAsFixed(0)}% Match',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.green.shade700,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),
          Text(
            context.tr('why_match_desc'),
            style: TextStyle(
              color: Colors.grey.shade600,
              fontSize: 12,
            ),
          ),

          const Divider(height: 24),

          // Quick Fact Pills
          if (distanceKm != null || etaMinutes != null) ...[
            Row(
              children: [
                if (distanceKm != null)
                  Chip(
                    avatar: const Icon(Icons.place, size: 14, color: Colors.blue),
                    label: Text('${distanceKm!.toStringAsFixed(1)} km away'),
                    backgroundColor: Colors.blue.shade50,
                    visualDensity: VisualDensity.compact,
                  ),
                if (distanceKm != null && etaMinutes != null) const SizedBox(width: 8),
                if (etaMinutes != null)
                  Chip(
                    avatar: const Icon(Icons.timer, size: 14, color: Colors.orange),
                    label: Text('ETA: ~$etaMinutes mins'),
                    backgroundColor: Colors.orange.shade50,
                    visualDensity: VisualDensity.compact,
                  ),
              ],
            ),
            const SizedBox(height: 12),
          ],

          // List of Explainable Reasons
          if (reasons.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12.0),
              child: Text(
                'Matches routing and capacity requirements.',
                style: TextStyle(color: Colors.grey.shade700),
              ),
            )
          else
            ...reasons.map((r) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 6.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      r.isPositive ? Icons.check_circle : Icons.warning_amber_rounded,
                      color: r.isPositive ? Colors.green.shade600 : Colors.amber.shade700,
                      size: 18,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        r.label,
                        style: TextStyle(
                          fontSize: 13,
                          color: r.isPositive ? Colors.black87 : Colors.amber.shade900,
                          fontWeight: r.isPositive ? FontWeight.normal : FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),

          const SizedBox(height: 20),

          // Close Button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.teal.shade700,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
              child: Text(context.tr('close')),
            ),
          ),
        ],
      ),
    );
  }
}
