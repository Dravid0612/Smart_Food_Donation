import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:smart_food_waste_donation/core/localization/app_locale.dart';
import 'package:smart_food_waste_donation/models/performance_model.dart';
import 'package:smart_food_waste_donation/widgets/performance_card_widget.dart';
import 'package:smart_food_waste_donation/widgets/why_this_match_dialog.dart';

void main() {
  group('Performance & Reliability Models Test', () {
    test('PerformanceProfile.fromJson parses complete raw and derived metrics', () {
      final json = {
        'user_id': 12,
        'name': 'Ramesh Volunteer',
        'role': 'volunteer',
        'performance_status': 'RELIABLE',
        'admin_action_status': 'NORMAL',
        'admin_action_notes': null,
        'overall_reliability_score': 96.5,
        'trust_tier': 'Highly Reliable',
        'trust_badges': ['Fast Responder', 'Punctual Courier', 'Verified Courier'],
        'recent_trend': 'improving',
        'trend_description': 'On-time rate and completion improving recently',
        'has_sufficient_history': true,
        'sample_size_threshold': 3,
        'recency_window_size': 10,
        'raw_metrics': {
          'total_tasks_assigned': 15,
          'total_tasks_accepted': 15,
          'total_completed': 14,
          'total_cancelled': 1,
          'total_no_shows': 0,
          'total_on_time': 13,
          'total_delayed': 1,
          'total_feedbacks_received': 14,
          'average_response_time_seconds': 95.0,
        },
        'derived_metrics': {
          'completion_rate_percent': 93.3,
          'on_time_rate_percent': 92.9,
          'cancellation_rate_percent': 6.7,
          'no_show_rate_percent': 0.0,
          'service_quality_score_percent': 98.0,
          'response_speed_score_percent': 95.0,
        },
        'dimensions': [
          {
            'name': 'Task Completion Rate',
            'score': 93.3,
            'weight': 0.35,
            'description': '14 of 15 rescues delivered successfully',
          }
        ],
      };

      final profile = PerformanceProfile.fromJson(json);

      expect(profile.userId, 12);
      expect(profile.name, 'Ramesh Volunteer');
      expect(profile.performanceStatus, 'RELIABLE');
      expect(profile.overallReliabilityScore, 96.5);
      expect(profile.trustBadges.length, 3);
      expect(profile.rawMetrics.totalCompleted, 14);
      expect(profile.rawMetrics.averageResponseTimeSeconds, 95.0);
      expect(profile.derivedMetrics.completionRatePercent, 93.3);
      expect(profile.recentTrend, 'improving');
    });

    test('AdminPerformanceOverview.fromJson parses network KPIs', () {
      final json = {
        'total_active_volunteers': 45,
        'total_verified_ngos': 18,
        'average_pickup_time_minutes': 14.5,
        'average_volunteer_response_time_seconds': 110.0,
        'volunteer_acceptance_rate_percent': 96.0,
        'network_on_time_rate_percent': 94.2,
        'network_completion_rate_percent': 98.1,
        'overall_rescue_success_rate_percent': 97.5,
        'fallback_escalation_rate_percent': 4.2,
        'needs_review_count': 2,
        'critical_alerts_count': 0,
      };

      final overview = AdminPerformanceOverview.fromJson(json);

      expect(overview.totalActiveVolunteers, 45);
      expect(overview.overallRescueSuccessRatePercent, 97.5);
      expect(overview.averageVolunteerResponseTimeSeconds, 110.0);
      expect(overview.needsReviewCount, 2);
    });

    test('RescueFailureAnalytics.fromJson parses failure categories', () {
      final json = {
        'total_rescue_attempts': 120,
        'total_completed_rescues': 115,
        'total_failed_or_cancelled': 5,
        'rescue_success_rate_percent': 95.8,
        'failure_reasons': [
          {
            'reason_code': 'volunteer_cancellation',
            'reason_label': 'Volunteer Cancelled Task',
            'count': 3,
            'percentage': 60.0,
            'trend': 'stable',
          },
          {
            'reason_code': 'pickup_delay',
            'reason_label': 'Severe Pickup Delay',
            'count': 2,
            'percentage': 40.0,
            'trend': 'stable',
          }
        ],
        'period': 'all_time',
      };

      final analytics = RescueFailureAnalytics.fromJson(json);

      expect(analytics.totalRescueAttempts, 120);
      expect(analytics.failureReasons.length, 2);
      expect(analytics.failureReasons[0].percentage, 60.0);
    });
  });

  group('PerformanceCardWidget UI Tests', () {
    testWidgets('Renders constructive reliability score, badges, and metrics', (WidgetTester tester) async {
      final profile = PerformanceProfile(
        userId: 1,
        name: 'Courier Test',
        role: 'volunteer',
        performanceStatus: 'RELIABLE',
        adminActionStatus: 'NORMAL',
        overallReliabilityScore: 94.0,
        trustTier: 'Highly Reliable',
        trustBadges: ['Fast Responder', 'Punctual Courier'],
        recentTrend: 'improving',
        trendDescription: 'On-time rate and completion improving recently',
        hasSufficientHistory: true,
        sampleSizeThreshold: 3,
        recencyWindowSize: 10,
        rawMetrics: RawOperationalMetrics(
          totalTasksAssigned: 10,
          totalTasksAccepted: 10,
          totalCompleted: 10,
          totalCancelled: 0,
          totalNoShows: 0,
          totalOnTime: 10,
          totalDelayed: 0,
          totalFeedbacksReceived: 10,
          averageResponseTimeSeconds: 60.0,
        ),
        derivedMetrics: DerivedReliabilityMetrics(
          completionRatePercent: 100.0,
          onTimeRatePercent: 100.0,
          cancellationRatePercent: 0.0,
          noShowRatePercent: 0.0,
          serviceQualityScorePercent: 100.0,
          responseSpeedScorePercent: 100.0,
        ),
        dimensions: [],
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => LocaleProvider()),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: PerformanceCardWidget(profile: profile),
            ),
          ),
        ),
      );

      expect(find.text('Highly Reliable'), findsOneWidget);
      expect(find.text('94%'), findsOneWidget);
      expect(find.text('Fast Responder'), findsOneWidget);
      expect(find.text('Punctual Courier'), findsOneWidget);
      expect(find.text('On-time rate and completion improving recently'), findsOneWidget);
    });
  });

  group('WhyThisMatchDialog UI Tests', () {
    testWidgets('Renders explainable matching reasons with positive icons', (WidgetTester tester) async {
      final reasons = [
        MatchReasonItem(code: 'available', label: 'Available now', isPositive: true),
        MatchReasonItem(code: 'capacity', label: 'Vehicle capacity sufficient (50 meals)', isPositive: true),
        MatchReasonItem(code: 'feasibility', label: 'Rescue feasible (ETA: 8m, Window: 180m)', isPositive: true),
      ];

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => LocaleProvider()),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () {
                    WhyThisMatchDialog.show(
                      context,
                      title: 'Why this match?',
                      participantName: 'Volunteer Senthil',
                      role: 'volunteer',
                      score: 95.0,
                      reasons: reasons,
                      distanceKm: 2.5,
                      etaMinutes: 8,
                    );
                  },
                  child: const Text('Open'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      expect(find.text('Why this match?'), findsOneWidget);
      expect(find.text('Volunteer Senthil'), findsOneWidget);
      expect(find.text('95% Match'), findsOneWidget);
      expect(find.text('Available now'), findsOneWidget);
      expect(find.text('Vehicle capacity sufficient (50 meals)'), findsOneWidget);
      expect(find.text('Rescue feasible (ETA: 8m, Window: 180m)'), findsOneWidget);
    });
  });

  group('Performance Localization Tests', () {
    test('Localization keys resolve in English, Tamil, and Hindi', () {
      final localeProvider = LocaleProvider();

      // English
      localeProvider.setLanguage('en');
      expect(localeProvider.translate('operational_performance'), 'Operational Performance');
      expect(localeProvider.translate('why_this_match'), 'Why this match?');
      expect(localeProvider.translate('admin_performance_hub'), 'Performance & Failure Intelligence');

      // Tamil
      localeProvider.setLanguage('ta');
      expect(localeProvider.translate('operational_performance'), 'செயல்பாட்டுத் திறன்');
      expect(localeProvider.translate('why_this_match'), 'இந்த பொருத்தம் ஏன்?');

      // Hindi
      localeProvider.setLanguage('hi');
      expect(localeProvider.translate('operational_performance'), 'परिचालन प्रदर्शन');
      expect(localeProvider.translate('why_this_match'), 'यह मिलान क्यों?');
    });
  });
}
