import 'package:flutter/material.dart';
import '../localization/app_locale.dart';

/// Semantic Visual Condition presentation item
class VisualConditionPresentation {
  final String rawKey;
  final String label;
  final IconData icon;
  final Color color;
  final Color backgroundColor;
  final Color borderColor;
  final String? confidenceDescription;

  const VisualConditionPresentation({
    required this.rawKey,
    required this.label,
    required this.icon,
    required this.color,
    required this.backgroundColor,
    required this.borderColor,
    this.confidenceDescription,
  });
}

/// Semantic Rescue Urgency presentation item
class RescueUrgencyPresentation {
  final String rawKey;
  final String label;
  final IconData icon;
  final Color color;
  final Color backgroundColor;
  final Color borderColor;
  final bool isWindowEnded;
  final bool isCritical;

  const RescueUrgencyPresentation({
    required this.rawKey,
    required this.label,
    required this.icon,
    required this.color,
    required this.backgroundColor,
    required this.borderColor,
    this.isWindowEnded = false,
    this.isCritical = false,
  });
}

/// Semantic Rescue Window Time presentation item
class RescueWindowPresentation {
  final int remainingMinutes;
  final String timeRemainingText;
  final String fullDisplayText;
  final Color ringColor;
  final bool isWindowEnded;
  final bool isUrgentOrCritical;

  const RescueWindowPresentation({
    required this.remainingMinutes,
    required this.timeRemainingText,
    required this.fullDisplayText,
    required this.ringColor,
    required this.isWindowEnded,
    required this.isUrgentOrCritical,
  });
}

/// Semantic Rescue Feasibility presentation item
class RescueFeasibilityPresentation {
  final String rawKey;
  final String label;
  final IconData icon;
  final Color color;
  final bool isFeasible;
  final bool canAcceptDonation;

  const RescueFeasibilityPresentation({
    required this.rawKey,
    required this.label,
    required this.icon,
    required this.color,
    required this.isFeasible,
    required this.canAcceptDonation,
  });
}

/// Centralized presentation helper for Food Rescue UI dimensions:
/// 1. Visual Condition (GOOD / FAIR / CONCERNING / UNCERTAIN)
/// 2. Rescue Urgency (FRESH / APPROACHING / URGENT / CRITICAL / RESCUE WINDOW ENDED)
/// 3. Rescue Window (Remaining time countdown)
/// 4. Feasibility (Feasible / At Risk / Unlikely / Window Ended)
class FoodRescueStatusHelper {
  /// ─── 1. VISUAL CONDITION ──────────────────────────────────────────────────
  static VisualConditionPresentation getVisualCondition(
    BuildContext context,
    String? rawCondition, {
    double? confidence,
  }) {
    final norm = (rawCondition ?? 'GOOD').toUpperCase().trim();
    String label;
    IconData icon;
    Color color;

    switch (norm) {
      case 'GOOD':
        label = context.trVisual('good');
        icon = Icons.check_circle_outline;
        color = const Color(0xFF2F6B4F); // Sabzi Green / Success
        break;
      case 'FAIR':
        label = context.trVisual('fair');
        icon = Icons.info_outline;
        color = const Color(0xFFE8A33D); // Amber / Warning
        break;
      case 'CONCERNING':
      case 'POOR':
      case 'SPOILAGE_SUSPECTED':
        label = (norm == 'SPOILAGE_SUSPECTED' || norm == 'POOR')
            ? context.trVisual('spoilage_suspected')
            : context.trVisual('concerning');
        icon = Icons.warning_amber_rounded;
        color = const Color(0xFFD9534F); // Orange-Red / Error
        break;
      case 'UNCERTAIN':
      default:
        label = context.trVisual('uncertain');
        icon = Icons.help_outline;
        color = const Color(0xFF64748B); // Slate / Neutral
        break;
    }

    String? confDesc;
    if (confidence != null && confidence > 0) {
      final confPct = (confidence * 100).toInt();
      confDesc = '${context.tr('ai_observation_confidence')}: $confPct%';
    }

    return VisualConditionPresentation(
      rawKey: norm,
      label: label,
      icon: icon,
      color: color,
      backgroundColor: color.withValues(alpha: 0.08),
      borderColor: color.withValues(alpha: 0.25),
      confidenceDescription: confDesc,
    );
  }

  /// ─── 2. RESCUE URGENCY ────────────────────────────────────────────────────
  static RescueUrgencyPresentation getRescueUrgency(
    BuildContext context,
    String? rawUrgency, {
    int? remainingMinutes,
  }) {
    final norm = (rawUrgency ?? 'FRESH').toUpperCase().trim();
    final isEnded = (remainingMinutes != null && remainingMinutes <= 0) ||
        norm == 'EXPIRED' ||
        norm == 'WINDOW_ENDED' ||
        norm == 'RESCUE_WINDOW_ENDED';

    if (isEnded) {
      const color = Color(0xFFC4432B); // Chili Red
      return RescueUrgencyPresentation(
        rawKey: 'WINDOW_ENDED',
        label: context.trUrgency('window_ended'),
        icon: Icons.cancel_outlined,
        color: color,
        backgroundColor: color.withValues(alpha: 0.1),
        borderColor: color.withValues(alpha: 0.3),
        isWindowEnded: true,
        isCritical: true,
      );
    }

    switch (norm) {
      case 'CRITICAL':
      case 'EMERGENCY':
        const color = Color(0xFFC4432B); // Chili Red
        return RescueUrgencyPresentation(
          rawKey: 'CRITICAL',
          label: context.trUrgency('critical'),
          icon: Icons.error_outline,
          color: color,
          backgroundColor: color.withValues(alpha: 0.1),
          borderColor: color.withValues(alpha: 0.3),
          isCritical: true,
        );
      case 'URGENT':
        const color = Color(0xFFE06A26); // Terracotta Orange
        return RescueUrgencyPresentation(
          rawKey: 'URGENT',
          label: context.trUrgency('urgent'),
          icon: Icons.warning_amber_rounded,
          color: color,
          backgroundColor: color.withValues(alpha: 0.1),
          borderColor: color.withValues(alpha: 0.3),
          isCritical: true,
        );
      case 'APPROACHING':
      case 'USE SOON':
      case 'USE_SOON':
        const color = Color(0xFFE8A33D); // Marigold Amber
        return RescueUrgencyPresentation(
          rawKey: 'APPROACHING',
          label: context.trUrgency('approaching'),
          icon: Icons.access_time,
          color: color,
          backgroundColor: color.withValues(alpha: 0.1),
          borderColor: color.withValues(alpha: 0.3),
        );
      case 'FRESH':
      case 'NORMAL':
      default:
        const color = Color(0xFF2F6B4F); // Sabzi Green
        return RescueUrgencyPresentation(
          rawKey: 'FRESH',
          label: context.trUrgency('fresh'),
          icon: Icons.eco,
          color: color,
          backgroundColor: color.withValues(alpha: 0.1),
          borderColor: color.withValues(alpha: 0.3),
        );
    }
  }

  /// ─── 3. RESCUE WINDOW (TIME REMAINING) ────────────────────────────────────
  static RescueWindowPresentation getRescueWindow(
    BuildContext context,
    int remainingMinutes, {
    String? urgencyOverride,
  }) {
    if (remainingMinutes <= 0) {
      return RescueWindowPresentation(
        remainingMinutes: 0,
        timeRemainingText: context.tr('rescue_window_ended'),
        fullDisplayText: context.tr('rescue_window_ended_desc'),
        ringColor: const Color(0xFFC4432B),
        isWindowEnded: true,
        isUrgentOrCritical: true,
      );
    }

    final String timeStr;
    if (remainingMinutes < 60) {
      timeStr = '${remainingMinutes}m';
    } else {
      final hours = remainingMinutes ~/ 60;
      final mins = remainingMinutes % 60;
      timeStr = mins > 0 ? '${hours}h ${mins}m' : '${hours}h';
    }

    final fullDisplay = context.trRemainingMinutes(remainingMinutes);

    Color ringColor;
    final u = (urgencyOverride ?? '').toUpperCase();
    if (u == 'CRITICAL' || remainingMinutes <= 45) {
      ringColor = const Color(0xFFC4432B); // Chili
    } else if (u == 'URGENT' || remainingMinutes <= 120) {
      ringColor = const Color(0xFFE06A26); // Orange
    } else if (u == 'APPROACHING' || remainingMinutes <= 240) {
      ringColor = const Color(0xFFE8A33D); // Amber
    } else {
      ringColor = const Color(0xFF2F6B4F); // Sabzi Green
    }

    return RescueWindowPresentation(
      remainingMinutes: remainingMinutes,
      timeRemainingText: timeStr,
      fullDisplayText: fullDisplay,
      ringColor: ringColor,
      isWindowEnded: false,
      isUrgentOrCritical: remainingMinutes <= 120,
    );
  }

  /// Helper to calculate remaining minutes from ISO expiry string safely
  static int calculateRemainingMinutes(String? expiryIsoString, [int defaultMinutes = 120]) {
    if (expiryIsoString == null || expiryIsoString.isEmpty) return defaultMinutes;
    final expiry = DateTime.tryParse(expiryIsoString);
    if (expiry == null) return defaultMinutes;
    final diff = expiry.difference(DateTime.now());
    if (diff.isNegative) return 0;
    return diff.inMinutes;
  }

  /// ─── 4. RESCUE FEASIBILITY ───────────────────────────────────────────────
  static RescueFeasibilityPresentation getRescueFeasibility(
    BuildContext context, {
    String? rawFeasibility,
    bool? isFeasible,
    int? remainingMinutes,
  }) {
    final norm = (rawFeasibility ?? 'RESCUE_FEASIBLE').toUpperCase().trim();
    final isWindowEnded = remainingMinutes != null && remainingMinutes <= 0;

    if (isWindowEnded) {
      return RescueFeasibilityPresentation(
        rawKey: 'WINDOW_ENDED',
        label: context.trFeasibility('window_ended'),
        icon: Icons.cancel_outlined,
        color: const Color(0xFFC4432B),
        isFeasible: false,
        canAcceptDonation: false,
      );
    }

    if (norm == 'RESCUE_FEASIBLE' || norm == 'FEASIBLE' || isFeasible == true) {
      return RescueFeasibilityPresentation(
        rawKey: 'RESCUE_FEASIBLE',
        label: context.trFeasibility('rescue_feasible'),
        icon: Icons.check_circle_outline,
        color: const Color(0xFF2F6B4F),
        isFeasible: true,
        canAcceptDonation: true,
      );
    } else if (norm == 'AT_RISK' || norm == 'TIGHT') {
      return RescueFeasibilityPresentation(
        rawKey: 'AT_RISK',
        label: context.trFeasibility('at_risk'),
        icon: Icons.warning_amber_rounded,
        color: const Color(0xFFE8A33D),
        isFeasible: true,
        canAcceptDonation: true,
      );
    } else {
      // INFEASIBLE / RESCUE_UNLIKELY / HIGH_RISK
      return RescueFeasibilityPresentation(
        rawKey: 'RESCUE_UNLIKELY',
        label: context.trFeasibility('rescue_unlikely'),
        icon: Icons.error_outline,
        color: const Color(0xFFC4432B),
        isFeasible: false,
        canAcceptDonation: false,
      );
    }
  }

  /// ─── 5. NEXT ACTION ADVICE ───────────────────────────────────────────────
  static String getNextActionAdvice(BuildContext context, {required String role, required int remainingMinutes, required String status}) {
    final st = status.toLowerCase();
    if (st == 'completed' || st == 'delivered') {
      return context.tr('status_completed');
    }
    if (remainingMinutes <= 0 || st == 'expired' || st == 'cancelled') {
      return context.tr('rescue_window_ended_advice');
    }
    if (remainingMinutes <= 45) {
      return context.tr('action_expedite_pickup');
    }
    return context.tr('action_standard_pickup');
  }
}
