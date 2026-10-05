import 'package:flutter/material.dart';

/// Design tokens for Smart Donor.
///
/// These values match the agreed design system used across every role's
/// UI. Keep this file as the single source of truth for color and type —
/// screens should reference [AppColors] / [AppTextStyles] rather than
/// hardcoding hex values, so the whole app stays visually consistent.
class AppColors {
  AppColors._();

  static const Color sabziGreen = Color(0xFF2F6B4F);
  static const Color deepSabzi = Color(0xFF1E2A22);
  static const Color leafMist = Color(0xFFF2F5EE);
  static const Color surfaceWhite = Color(0xFFFFFFFF);
  static const Color marigold = Color(0xFFE8A33D);
  static const Color chili = Color(0xFFC4432B);
  static const Color tiffinTeal = Color(0xFF3E6E72);
  static const Color sageGrey = Color(0xFF5B6B60);
  static const Color hairline = Color(0xFFDCE3D9);
}

class AppTextStyles {
  AppTextStyles._();

  /// NotoSans is chosen because it renders English, Tamil and Hindi with
  /// matching weight and spacing. Register NotoSans / NotoSansDevanagari /
  /// NotoSansTamil as font assets in pubspec.yaml for this to take full
  /// effect — if the font isn't bundled yet, Flutter falls back to the
  /// platform default instead of failing the build.
  static const String fontFamily = 'NotoSans';

  static const TextStyle h1 = TextStyle(
    fontFamily: fontFamily,
    fontSize: 24,
    fontWeight: FontWeight.w600,
    color: AppColors.deepSabzi,
  );

  static const TextStyle h2 = TextStyle(
    fontFamily: fontFamily,
    fontSize: 18,
    fontWeight: FontWeight.w600,
    color: AppColors.deepSabzi,
  );

  static const TextStyle body = TextStyle(
    fontFamily: fontFamily,
    fontSize: 15,
    fontWeight: FontWeight.w400,
    color: AppColors.deepSabzi,
  );

  static const TextStyle bodySmall = TextStyle(
    fontFamily: fontFamily,
    fontSize: 13,
    fontWeight: FontWeight.w400,
    color: AppColors.sageGrey,
  );

  static const TextStyle label = TextStyle(
    fontFamily: fontFamily,
    fontSize: 12,
    fontWeight: FontWeight.w500,
    color: AppColors.sageGrey,
    letterSpacing: 0.2,
  );
}

class AppTheme {
  AppTheme._();

  static ThemeData get light {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: AppColors.leafMist,
      fontFamily: AppTextStyles.fontFamily,
      colorScheme: ColorScheme.fromSeed(seedColor: AppColors.sabziGreen),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.sabziGreen,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppColors.sabziGreen.withOpacity(0.5),
          minimumSize: const Size.fromHeight(56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontFamily: AppTextStyles.fontFamily,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.deepSabzi,
          side: const BorderSide(color: AppColors.hairline),
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceWhite,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.hairline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.hairline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide:
              const BorderSide(color: AppColors.sabziGreen, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.chili),
        ),
        hintStyle: const TextStyle(color: AppColors.sageGrey),
      ),
    );
  }

  /// Backward-compatible alias for existing test suites and router
  static ThemeData get lightTheme => light;

  // Compatibility Tokens mapped to AppColors
  static const Color primaryGreen = AppColors.sabziGreen;
  static const Color primaryDark = AppColors.deepSabzi;
  static const Color primaryLight = AppColors.sabziGreen;
  static const Color primarySoft = AppColors.leafMist;
  static const Color primaryAccent = AppColors.sabziGreen;
  static const Color secondaryTerracotta = AppColors.chili;
  static const Color secondaryLight = AppColors.marigold;

  // Background & Surface Tokens
  static const Color surface = AppColors.surfaceWhite;
  static const Color background = AppColors.leafMist;
  static const Color card = AppColors.surfaceWhite;
  static const Color surfaceHighlight = AppColors.leafMist;
  static const Color surfaceWarm = AppColors.leafMist;

  // Text Tokens
  static const Color textPrimary = AppColors.deepSabzi;
  static const Color textSecondary = AppColors.sageGrey;
  static const Color textMuted = AppColors.sageGrey;
  static const Color border = AppColors.hairline;
  static const Color borderLight = AppColors.hairline;
  static const Color divider = AppColors.hairline;

  // Semantic Feedback Tokens
  static const Color success = AppColors.sabziGreen;
  static const Color successLight = AppColors.leafMist;
  static const Color warning = AppColors.marigold;
  static const Color warningLight = AppColors.leafMist;
  static const Color error = AppColors.chili;
  static const Color errorLight = AppColors.leafMist;
  static const Color info = AppColors.tiffinTeal;
  static const Color infoLight = AppColors.leafMist;
  static const Color admin = AppColors.tiffinTeal;
  static const Color adminLight = AppColors.leafMist;
  static const Color disabled = AppColors.hairline;

  // Status & Urgency Tokens
  static const Color statusPending = AppColors.tiffinTeal;
  static const Color statusAccepted = AppColors.marigold;
  static const Color statusAssigned = AppColors.tiffinTeal;
  static const Color statusCollected = AppColors.marigold;
  static const Color statusDelivered = AppColors.sabziGreen;
  static const Color statusCompleted = AppColors.sabziGreen;
  static const Color statusExpired = AppColors.sageGrey;
  static const Color statusCancelled = AppColors.chili;

  static const Color urgencyFresh = AppColors.sabziGreen;
  static const Color urgencyUseSoon = AppColors.marigold;
  static const Color urgencyApproaching = AppColors.marigold;
  static const Color urgencyUrgent = AppColors.marigold;
  static const Color urgencyCritical = AppColors.chili;
  static const Color urgencyExpired = AppColors.sageGrey;

  static const Color trustTeal = AppColors.tiffinTeal;
  static const Color urgentAmber = AppColors.marigold;
  static const Color criticalCrimson = AppColors.chili;

  // 8-Point Spacing System
  static const double space2 = 2.0;
  static const double space4 = 4.0;
  static const double space6 = 6.0;
  static const double space8 = 8.0;
  static const double space10 = 10.0;
  static const double space12 = 12.0;
  static const double space14 = 14.0;
  static const double space16 = 16.0;
  static const double space20 = 20.0;
  static const double space24 = 24.0;
  static const double space28 = 28.0;
  static const double space32 = 32.0;
  static const double space40 = 40.0;
  static const double space48 = 48.0;
  static const double space56 = 56.0;
  static const double space64 = 64.0;

  // Border Radius Tokens
  static const double radiusXS = 4.0;
  static const double radiusSmall = 8.0;
  static const double radiusInput = 10.0;
  static const double radiusMedium = 12.0;
  static const double radiusCard = 16.0;
  static const double radiusFeatureCard = 20.0;
  static const double radiusButton = 12.0;
  static const double radiusPill = 999.0;

  // Shadows
  static List<BoxShadow> get shadowCard => [
    BoxShadow(
      color: AppColors.deepSabzi.withValues(alpha: 0.04),
      blurRadius: 10,
      offset: const Offset(0, 3),
    ),
  ];

  static List<BoxShadow> get shadowFeature => [
    BoxShadow(
      color: AppColors.sabziGreen.withValues(alpha: 0.08),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
  ];

  static List<BoxShadow> get shadowElevated => [
    BoxShadow(
      color: AppColors.deepSabzi.withValues(alpha: 0.08),
      blurRadius: 20,
      offset: const Offset(0, 8),
    ),
  ];
}
