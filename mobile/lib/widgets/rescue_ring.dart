import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../core/localization/app_locale.dart';
import '../core/theme/app_theme.dart';

/// Signature Design Element: Rescue Ring
/// Circular countdown & time urgency visualization representing TIME remaining in the estimated rescue window.
///
/// States:
/// - FRESH (> 2h remaining): Sabzi Green (#2F6B4F)
/// - APPROACHING (30m - 2h remaining): Marigold Amber (#E8A33D)
/// - URGENT (< 30m remaining): Terracotta Orange (#E06A26)
/// - CRITICAL / WINDOW ENDED (<= 0m or Escalated): Chili Red (#C4432B)
class RescueRing extends StatelessWidget {
  final int remainingMinutes;
  final int totalWindowMinutes;
  final double size;
  final double strokeWidth;
  final bool showLabel;
  final String? urgencyOverride;

  const RescueRing({
    super.key,
    required this.remainingMinutes,
    this.totalWindowMinutes = 180,
    this.size = 64.0,
    this.strokeWidth = 6.0,
    this.showLabel = true,
    this.urgencyOverride,
  });

  /// Factory preset for compact card display (e.g. inside list items)
  factory RescueRing.compact({
    Key? key,
    required int remainingMinutes,
    int totalWindowMinutes = 180,
    String? urgencyOverride,
  }) {
    return RescueRing(
      key: key,
      remainingMinutes: remainingMinutes,
      totalWindowMinutes: totalWindowMinutes,
      size: 48.0,
      strokeWidth: 4.5,
      showLabel: true,
      urgencyOverride: urgencyOverride,
    );
  }

  /// Factory preset for large hero display (e.g. AI analysis or active task)
  factory RescueRing.hero({
    Key? key,
    required int remainingMinutes,
    int totalWindowMinutes = 180,
    String? urgencyOverride,
  }) {
    return RescueRing(
      key: key,
      remainingMinutes: remainingMinutes,
      totalWindowMinutes: totalWindowMinutes,
      size: 110.0,
      strokeWidth: 9.0,
      showLabel: true,
      urgencyOverride: urgencyOverride,
    );
  }

  Color get _ringColor {
    final urgency = urgencyOverride?.toUpperCase() ?? '';
    if (urgency == 'CRITICAL' || urgency == 'WINDOW_ENDED' || urgency == 'EXPIRED' || remainingMinutes <= 0) {
      return const Color(0xFFC4432B); // Chili Red
    } else if (urgency == 'URGENT' || remainingMinutes < 30) {
      return const Color(0xFFE06A26); // Terracotta Orange
    } else if (urgency == 'APPROACHING' || remainingMinutes <= 120) {
      return const Color(0xFFE8A33D); // Marigold Amber
    } else {
      return const Color(0xFF2F6B4F); // Sabzi Green
    }
  }

  String _formatTime() {
    if (remainingMinutes <= 0) {
      return '--';
    } else if (remainingMinutes < 60) {
      return '${remainingMinutes}m';
    } else {
      final hours = remainingMinutes ~/ 60;
      final mins = remainingMinutes % 60;
      return mins > 0 ? '${hours}h ${mins}m' : '${hours}h';
    }
  }

  @override
  Widget build(BuildContext context) {
    final progress = totalWindowMinutes > 0
        ? (remainingMinutes / totalWindowMinutes).clamp(0.0, 1.0)
        : 0.0;
    final ringColor = _ringColor;
    final isEnded = remainingMinutes <= 0;

    return Semantics(
      label: isEnded
          ? context.tr('rescue_window_ended_desc')
          : 'Rescue Window: ${context.trRemainingMinutes(remainingMinutes)}',
      child: SizedBox(
        width: size,
        height: size,
        child: Stack(
          alignment: Alignment.center,
          children: [
            CustomPaint(
              size: Size(size, size),
              painter: _RescueRingPainter(
                progress: isEnded ? 0.0 : progress,
                strokeWidth: strokeWidth,
                activeColor: ringColor,
                trackColor: ringColor.withValues(alpha: 0.15),
              ),
            ),
            if (showLabel)
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _formatTime(),
                    style: TextStyle(
                      fontFamily: 'NotoSans',
                      fontSize: size >= 90 ? 20 : (size >= 60 ? 14 : 11),
                      fontWeight: FontWeight.bold,
                      color: isEnded ? const Color(0xFFC4432B) : AppTheme.textPrimary,
                      height: 1.1,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                  if (size >= 80)
                    Text(
                      isEnded
                          ? context.trUrgency('window_ended')
                          : context.tr('remaining_minutes').split(' ').first,
                      style: TextStyle(
                        fontSize: 9,
                        color: isEnded ? const Color(0xFFC4432B) : AppTheme.textSecondary,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.2,
                      ),
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _RescueRingPainter extends CustomPainter {
  final double progress;
  final double strokeWidth;
  final Color activeColor;
  final Color trackColor;

  _RescueRingPainter({
    required this.progress,
    required this.strokeWidth,
    required this.activeColor,
    required this.trackColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;

    // Background track ring
    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, radius, trackPaint);

    // Active progress arc
    if (progress > 0) {
      final activePaint = Paint()
        ..color = activeColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;

      // Start at 12 o'clock (-90 degrees)
      const startAngle = -math.pi / 2;
      final sweepAngle = 2 * math.pi * progress;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweepAngle,
        false,
        activePaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _RescueRingPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.activeColor != activeColor ||
        oldDelegate.strokeWidth != strokeWidth;
  }
}
