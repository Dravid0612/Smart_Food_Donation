import 'package:flutter/material.dart';

/// Unified Humanitarian Logistics Design System Tokens for Smart Food Rescue
class AppTheme {
  // Brand Tokens
  static const Color primaryGreen = Color(0xFF2F7D32);
  static const Color primaryDark = Color(0xFF1B5E20);
  static const Color primaryLight = Color(0xFF4CAF50);
  static const Color primarySoft = Color(0xFFE8F5E9);
  static const Color primaryAccent = Color(0xFF81C784);
  static const Color secondaryTerracotta = Color(0xFFC96F4A);
  static const Color secondaryLight = Color(0xFFE8A88A);
  
  // Background & Surface Tokens
  static const Color surface = Color(0xFFFFFFFF);
  static const Color background = Color(0xFFF8F7F3);
  static const Color card = Color(0xFFFFFFFF);
  static const Color surfaceHighlight = Color(0xFFF0EBE1);
  static const Color surfaceWarm = Color(0xFFFAF7F2);
  
  // Text Tokens
  static const Color textPrimary = Color(0xFF162033);
  static const Color textSecondary = Color(0xFF667085);
  static const Color textMuted = Color(0xFF94A3B8);
  static const Color border = Color(0xFFE5E7EB);
  static const Color borderLight = Color(0xFFF1F5F9);
  static const Color divider = Color(0xFFE5E7EB);
  
  // Semantic Feedback Tokens
  static const Color success = Color(0xFF2E7D32);
  static const Color successLight = Color(0xFFDCFCE7);
  static const Color warning = Color(0xFFE8A33D);
  static const Color warningLight = Color(0xFFFEF3C7);
  static const Color error = Color(0xFFDC2626);
  static const Color errorLight = Color(0xFFFEE2E2);
  static const Color info = Color(0xFF2563EB);
  static const Color infoLight = Color(0xFFDBEAFE);
  static const Color admin = Color(0xFF7C3AED);
  static const Color adminLight = Color(0xFFEDE9FE);
  static const Color disabled = Color(0xFFCBD5E1);

  // Status & Urgency Tokens
  static const Color statusPending = Color(0xFF2563EB);     // Blue
  static const Color statusAccepted = Color(0xFFC96F4A);    // Terracotta
  static const Color statusAssigned = Color(0xFF0891B2);    // Cyan
  static const Color statusCollected = Color(0xFFD97706);   // Amber
  static const Color statusDelivered = Color(0xFF16A34A);   // Green
  static const Color statusCompleted = Color(0xFF15803D);   // Dark Green
  static const Color statusExpired = Color(0xFF64748B);     // Slate
  static const Color statusCancelled = Color(0xFFDC2626);   // Red

  static const Color urgencyFresh = Color(0xFF2E7D32);
  static const Color urgencyUseSoon = Color(0xFFE8A33D);
  static const Color urgencyApproaching = Color(0xFFE8A33D);
  static const Color urgencyUrgent = Color(0xFFEA580C);
  static const Color urgencyCritical = Color(0xFFC4432B);
  static const Color urgencyExpired = Color(0xFF64748B);

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

  // Elevation & Shadows
  static List<BoxShadow> get shadowCard => [
    BoxShadow(
      color: const Color(0xFF162033).withValues(alpha: 0.04),
      blurRadius: 10,
      offset: const Offset(0, 3),
    ),
  ];

  static List<BoxShadow> get shadowFeature => [
    BoxShadow(
      color: primaryGreen.withValues(alpha: 0.08),
      blurRadius: 16,
      offset: const Offset(0, 4),
    ),
    BoxShadow(
      color: const Color(0xFF162033).withValues(alpha: 0.03),
      blurRadius: 4,
      offset: const Offset(0, 1),
    ),
  ];

  static List<BoxShadow> get shadowElevated => [
    BoxShadow(
      color: const Color(0xFF162033).withValues(alpha: 0.08),
      blurRadius: 20,
      offset: const Offset(0, 8),
    ),
  ];

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      fontFamily: 'Inter',
      colorScheme: const ColorScheme(
        brightness: Brightness.light,
        primary: primaryGreen,
        onPrimary: Colors.white,
        secondary: secondaryTerracotta,
        onSecondary: Colors.white,
        surface: surface,
        onSurface: textPrimary,
        error: error,
        onError: Colors.white,
      ),
      scaffoldBackgroundColor: background,
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        elevation: 0,
        centerTitle: false,
        scrolledUnderElevation: 1,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 19,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
        iconTheme: IconThemeData(color: textPrimary),
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radiusCard),
          side: const BorderSide(color: border, width: 1),
        ),
        margin: const EdgeInsets.symmetric(vertical: space8, horizontal: 0),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        elevation: 0,
        height: 64,
        indicatorColor: primaryGreen.withValues(alpha: 0.12),
        indicatorShape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusPill)),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const IconThemeData(color: primaryGreen, size: 22);
          }
          return const IconThemeData(color: textSecondary, size: 22);
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const TextStyle(color: primaryGreen, fontSize: 12, fontWeight: FontWeight.w700);
          }
          return const TextStyle(color: textSecondary, fontSize: 11, fontWeight: FontWeight.w500);
        }),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryGreen,
          foregroundColor: Colors.white,
          elevation: 0,
          minimumSize: const Size(64, 48),
          padding: const EdgeInsets.symmetric(horizontal: space24, vertical: space14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusButton),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.2,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primaryGreen,
          side: const BorderSide(color: primaryGreen, width: 1.5),
          padding: const EdgeInsets.symmetric(horizontal: space24, vertical: space14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radiusButton),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: card,
        contentPadding: const EdgeInsets.symmetric(horizontal: space16, vertical: space16),
        labelStyle: const TextStyle(color: textSecondary, fontSize: 14),
        hintStyle: const TextStyle(color: textMuted, fontSize: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusButton),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusButton),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusButton),
          borderSide: const BorderSide(color: primaryGreen, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radiusButton),
          borderSide: const BorderSide(color: error),
        ),
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontSize: 30, fontWeight: FontWeight.w800, color: textPrimary, letterSpacing: -0.6),
        displayMedium: TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: textPrimary, letterSpacing: -0.4),
        headlineLarge: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: textPrimary, letterSpacing: -0.3),
        titleLarge: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: textPrimary, letterSpacing: -0.2),
        titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: textPrimary),
        titleSmall: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: textPrimary),
        bodyLarge: TextStyle(fontSize: 15, fontWeight: FontWeight.normal, color: textPrimary, height: 1.45),
        bodyMedium: TextStyle(fontSize: 13, fontWeight: FontWeight.normal, color: textSecondary, height: 1.4),
        bodySmall: TextStyle(fontSize: 12, fontWeight: FontWeight.normal, color: textMuted),
        labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: textPrimary),
        labelMedium: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: textSecondary),
        labelSmall: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: textMuted),
      ),
    );
  }
}
