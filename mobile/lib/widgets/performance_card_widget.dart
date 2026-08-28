import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../models/performance_model.dart';

class PerformanceCardWidget extends StatefulWidget {
  final PerformanceProfile profile;
  final bool isCompact;

  const PerformanceCardWidget({
    super.key,
    required this.profile,
    this.isCompact = false,
  });

  @override
  State<PerformanceCardWidget> createState() => _PerformanceCardWidgetState();
}

class _PerformanceCardWidgetState extends State<PerformanceCardWidget> {
  bool _showRawMetrics = false;

  Color _getScoreColor(double score) {
    if (score >= 90.0) return Colors.green.shade700;
    if (score >= 75.0) return Colors.blue.shade700;
    if (score >= 60.0) return Colors.amber.shade800;
    return Colors.red.shade700;
  }

  Color _getTrendColor(String trend) {
    if (trend == 'improving') return Colors.green.shade700;
    if (trend == 'declining') return Colors.red.shade700;
    return Colors.teal.shade700;
  }

  IconData _getTrendIcon(String trend) {
    if (trend == 'improving') return Icons.trending_up;
    if (trend == 'declining') return Icons.trending_down;
    return Icons.trending_flat;
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.profile;
    final scoreColor = _getScoreColor(p.overallReliabilityScore);
    final trendColor = _getTrendColor(p.recentTrend);

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: scoreColor.withValues(alpha: 0.12),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(Icons.verified_user_outlined, color: scoreColor, size: 22),
                    ),
                    const SizedBox(width: 10),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          p.trustTier,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        Text(
                          p.hasSufficientHistory
                              ? '${p.rawMetrics.totalCompleted} ${context.tr('completed_rescues')}'
                              : context.tr('new_courier_tier'),
                          style: TextStyle(
                            color: Colors.grey.shade600,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                // Score Badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: scoreColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: scoreColor.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      Text(
                        '${p.overallReliabilityScore.toStringAsFixed(0)}%',
                        style: TextStyle(
                          color: scoreColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Icon(Icons.shield_outlined, color: scoreColor, size: 16),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),

            // Constructive Trend Banner
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: trendColor.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(_getTrendIcon(p.recentTrend), color: trendColor, size: 16),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      p.trendDescription.isNotEmpty
                          ? p.trendDescription
                          : (p.recentTrend == 'improving'
                              ? context.tr('improving_trend')
                              : context.tr('steady_trend')),
                      style: TextStyle(
                        color: trendColor,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),

            // Derived Metrics 3-Col Row
            Row(
              children: [
                Expanded(
                  child: _buildMetricItem(
                    label: context.tr('completion_rate'),
                    value: '${p.derivedMetrics.completionRatePercent.toStringAsFixed(0)}%',
                    icon: Icons.check_circle_outline,
                    color: Colors.green.shade700,
                  ),
                ),
                Expanded(
                  child: _buildMetricItem(
                    label: context.tr('on_time_rate'),
                    value: '${p.derivedMetrics.onTimeRatePercent.toStringAsFixed(0)}%',
                    icon: Icons.access_time,
                    color: Colors.blue.shade700,
                  ),
                ),
                Expanded(
                  child: _buildMetricItem(
                    label: context.tr('response_speed'),
                    value: '${(p.rawMetrics.averageResponseTimeSeconds / 60.0).toStringAsFixed(1)}m',
                    icon: Icons.speed,
                    color: Colors.purple.shade700,
                  ),
                ),
              ],
            ),

            // Badges
            if (p.trustBadges.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: p.trustBadges.map((badge) {
                  return Chip(
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    visualDensity: VisualDensity.compact,
                    backgroundColor: Colors.blueGrey.shade50,
                    side: BorderSide(color: Colors.blueGrey.shade200),
                    label: Text(
                      badge,
                      style: TextStyle(color: Colors.blueGrey.shade800, fontSize: 11),
                    ),
                    avatar: const Icon(Icons.star, color: Colors.amber, size: 14),
                  );
                }).toList(),
              ),
            ],

            // Raw Metrics Toggle & Breakdown
            if (!widget.isCompact) ...[
              const Divider(height: 24),
              InkWell(
                onTap: () {
                  setState(() {
                    _showRawMetrics = !_showRawMetrics;
                  });
                },
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      context.tr('raw_metrics_title'),
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: Colors.grey.shade700,
                      ),
                    ),
                    Icon(
                      _showRawMetrics ? Icons.expand_less : Icons.expand_more,
                      color: Colors.grey.shade600,
                    ),
                  ],
                ),
              ),
              if (_showRawMetrics) ...[
                const SizedBox(height: 10),
                _buildRawDataRow('Assigned Tasks', '${p.rawMetrics.totalTasksAssigned}'),
                _buildRawDataRow('Accepted Rescues', '${p.rawMetrics.totalTasksAccepted}'),
                _buildRawDataRow('Completed Deliveries', '${p.rawMetrics.totalCompleted}'),
                _buildRawDataRow('Cancelled Tasks', '${p.rawMetrics.totalCancelled}'),
                _buildRawDataRow('On-Time Handover Count', '${p.rawMetrics.totalOnTime}'),
                _buildRawDataRow('Feedbacks Logged', '${p.rawMetrics.totalFeedbacksReceived}'),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMetricItem({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 2),
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 15,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 10,
              color: Colors.grey.shade700,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildRawDataRow(String title, String val) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
          Text(val, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
        ],
      ),
    );
  }
}
