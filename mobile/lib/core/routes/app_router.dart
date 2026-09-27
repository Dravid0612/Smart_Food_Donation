import 'dart:convert';
import 'package:go_router/go_router.dart';
import '../../core/storage/secure_storage.dart';
import '../../screens/splash/splash_screen.dart';
import '../../screens/onboarding/onboarding_screen.dart';
import '../../screens/auth/login_screen.dart';
import '../../screens/auth/donor_login_screen.dart';
import '../../screens/auth/ngo_login_screen.dart';
import '../../screens/auth/volunteer_login_screen.dart';
import '../../screens/auth/admin_login_screen.dart';
import '../../screens/auth/register_screen.dart';
import '../../screens/auth/forgot_password_screen.dart';

// Donor
import '../../screens/donor/donor_dashboard.dart';
import '../../screens/donor/create_donation_screen.dart';
import '../../screens/donor/donation_detail_screen.dart';
import '../../screens/donor/donor_history_screen.dart';
import '../../screens/donor/donor_rewards_screen.dart';
import '../../screens/donor/donor_ai_analysis_screen.dart';
import '../../screens/donor/recurring_donations_screen.dart';
import '../../screens/donor/donation_certificate_screen.dart';
import '../../screens/donor/why_donate_screen.dart';
import '../../screens/donor/how_it_works_screen.dart';
import '../../screens/donor/donor_impact_dashboard_screen.dart';
import '../../screens/donor/donor_secure_otp_screen.dart';
import '../../screens/donor/quick_rescue_screen.dart';
import '../../screens/onboarding/donor_onboarding_screen.dart';

// NGO
import '../../screens/ngo/ngo_dashboard.dart';
import '../../screens/ngo/ngo_food_requirements_screen.dart';
import '../../screens/ngo/ngo_history_screen.dart';
import '../../screens/ngo/ngo_receiving_distribution_screen.dart';

// Volunteer
import '../../screens/volunteer/volunteer_dashboard.dart';
import '../../screens/volunteer/volunteer_pickup_request_screen.dart';
import '../../screens/volunteer/volunteer_active_task_screen.dart';
import '../../screens/volunteer/volunteer_impact_screen.dart';
import '../../screens/volunteer/volunteer_claim_screen.dart';
import '../../screens/volunteer/volunteer_vehicle_profile_screen.dart';
import '../../screens/volunteer/volunteer_task_history_screen.dart';

// Admin
import '../../screens/admin/admin_dashboard.dart';
import '../../screens/admin/admin_donations_screen.dart';
import '../../screens/admin/admin_users_screen.dart';
import '../../screens/admin/ngo_verification_screen.dart';
import '../../screens/admin/admin_interventions_screen.dart';
import '../../screens/admin/admin_disputes_screen.dart';
import '../../screens/admin/admin_performance_screen.dart';
import '../../screens/admin/admin_audit_log_screen.dart';

// Shared
import '../../screens/notifications/notification_center_screen.dart';
import '../../screens/profile/profile_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/login',
  redirect: (context, state) async {
    final storage = SecureStorageService();
    final token = await storage.getToken();
    final userData = await storage.getUserData();

    final location = state.matchedLocation;
    final isPublicRoute = location == '/' ||
        location == '/onboarding' ||
        location.startsWith('/login') ||
        location == '/register' ||
        location == '/forgot-password' ||
        location.startsWith('/claim');

    // 1. If not authenticated and trying to access protected route -> go to /login
    if (token == null || token.isEmpty || userData == null) {
      if (!isPublicRoute) return '/login';
      return null;
    }

    // 2. Parse authoritative role from verified local storage
    String role = 'donor';
    try {
      final Map<String, dynamic> userMap = jsonDecode(userData);
      role = (userMap['role'] ?? 'donor').toString().toLowerCase();
    } catch (_) {}

    // 3. If already logged in and visiting public auth screens, redirect to role dashboard
    if (location.startsWith('/login') || location == '/register' || location == '/forgot-password' || location == '/onboarding' || location == '/') {
      switch (role) {
        case 'ngo':
          return '/ngo';
        case 'volunteer':
          return '/volunteer';
        case 'admin':
          return '/admin';
        case 'donor':
        default:
          return '/donor';
      }
    }

    // 4. Role-based Route Protection (Strict Cross-Role Isolation)
    if (role == 'donor') {
      if (location.startsWith('/ngo') || location.startsWith('/volunteer') || location.startsWith('/admin')) {
        return '/donor';
      }
    } else if (role == 'ngo') {
      if (location.startsWith('/donor') || location.startsWith('/volunteer') || location.startsWith('/admin')) {
        return '/ngo';
      }
    } else if (role == 'volunteer') {
      if (location.startsWith('/donor') || location.startsWith('/ngo') || location.startsWith('/admin')) {
        return '/volunteer';
      }
    } else if (role == 'admin') {
      if (location.startsWith('/donor') || location.startsWith('/ngo') || location.startsWith('/volunteer')) {
        return '/admin';
      }
    }

    return null;
  },
  routes: [
    GoRoute(path: '/', builder: (context, state) => const SplashScreen()),
    GoRoute(path: '/onboarding', builder: (context, state) => const OnboardingScreen()),
    GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
    GoRoute(path: '/login/donor', builder: (context, state) => const DonorLoginScreen()),
    GoRoute(path: '/login/ngo', builder: (context, state) => const NgoLoginScreen()),
    GoRoute(path: '/login/volunteer', builder: (context, state) => const VolunteerLoginScreen()),
    GoRoute(path: '/login/admin', builder: (context, state) => const AdminLoginScreen()),
    GoRoute(path: '/forgot-password', builder: (context, state) => const ForgotPasswordScreen()),
    GoRoute(
      path: '/register',
      builder: (context, state) {
        String? role;
        if (state.extra is Map<String, dynamic>) {
          role = (state.extra as Map<String, dynamic>)['role'] as String?;
        } else if (state.extra is String) {
          role = state.extra as String;
        }
        return RegisterScreen(initialRole: role);
      },
    ),

    // ─── Donor Routes ───────────────────────────────────────────────────────
    GoRoute(path: '/donor', builder: (context, state) => const DonorDashboardScreen()),
    GoRoute(path: '/donor/history', builder: (context, state) => const DonorHistoryScreen()),
    GoRoute(path: '/donor/recurring', builder: (context, state) => const RecurringDonationsScreen()),
    GoRoute(
      path: '/donor/create',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>?;
        return CreateDonationScreen(aiData: extra);
      },
    ),
    GoRoute(
      path: '/donor/quick-rescue',
      builder: (context, state) {
        final extra = state.extra as String?;
        return QuickRescueScreen(initialImagePath: extra);
      },
    ),
    GoRoute(
      path: '/donor/detail/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return DonationDetailScreen(donationId: id);
      },
    ),
    GoRoute(
      path: '/donor/certificate/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return DonationCertificateScreen(donationId: id);
      },
    ),
    GoRoute(
      path: '/donor/otp/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return DonorSecureOtpScreen(donationId: id);
      },
    ),
    GoRoute(path: '/donor/rewards', builder: (context, state) => const DonorRewardsScreen()),
    GoRoute(path: '/donor/why-donate', builder: (context, state) => const WhyDonateScreen()),
    GoRoute(path: '/donor/how-it-works', builder: (context, state) => const HowItWorksScreen()),
    GoRoute(path: '/donor/impact', builder: (context, state) => const DonorImpactDashboardScreen()),
    GoRoute(path: '/donor/onboarding', builder: (context, state) => const DonorOnboardingScreen()),
    GoRoute(
      path: '/donor/ai-analysis',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>?;
        return DonorAiAnalysisScreen(imagePath: extra?['imagePath'] as String?);
      },
    ),

    // ─── NGO Routes ─────────────────────────────────────────────────────────
    GoRoute(path: '/ngo', builder: (context, state) => const NgoDashboardScreen()),
    GoRoute(path: '/ngo/requirements', builder: (context, state) => const NgoFoodRequirementsScreen()),
    GoRoute(path: '/ngo/history', builder: (context, state) => const NgoHistoryScreen()),
    GoRoute(
      path: '/ngo/receiving/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return NgoReceivingDistributionScreen(donationId: id);
      },
    ),
    GoRoute(
      path: '/ngo/distribution/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return NgoReceivingDistributionScreen(donationId: id);
      },
    ),

    // ─── Volunteer Routes ────────────────────────────────────────────────────
    GoRoute(path: '/volunteer', builder: (context, state) => const VolunteerDashboardScreen()),
    GoRoute(path: '/volunteer/vehicle', builder: (context, state) => const VolunteerVehicleProfileScreen()),
    GoRoute(path: '/volunteer/history', builder: (context, state) => const VolunteerTaskHistoryScreen()),
    GoRoute(
      path: '/volunteer/request/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return VolunteerPickupRequestScreen(donationId: id);
      },
    ),
    GoRoute(
      path: '/volunteer/task/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return VolunteerActiveTaskScreen(donationId: id);
      },
    ),
    GoRoute(path: '/volunteer/impact', builder: (context, state) => const VolunteerImpactScreen()),

    // ─── Admin Routes ────────────────────────────────────────────────────────
    GoRoute(path: '/admin', builder: (context, state) => const AdminDashboardScreen()),
    GoRoute(path: '/admin/donations', builder: (context, state) => const AdminDonationsScreen()),
    GoRoute(path: '/admin/users', builder: (context, state) => const AdminUsersScreen()),
    GoRoute(path: '/admin/verify-ngos', builder: (context, state) => const NgoVerificationScreen()),
    GoRoute(path: '/admin/interventions', builder: (context, state) => const AdminInterventionsScreen()),
    GoRoute(path: '/admin/disputes', builder: (context, state) => const AdminDisputesScreen()),
    GoRoute(path: '/admin/performance', builder: (context, state) => const AdminPerformanceScreen()),
    GoRoute(path: '/admin/audit-logs', builder: (context, state) => const AdminAuditLogScreen()),

    // ─── Shared Routes ───────────────────────────────────────────────────────
    GoRoute(path: '/notifications', builder: (context, state) => const NotificationCenterScreen()),
    GoRoute(path: '/profile', builder: (context, state) => const ProfileScreen()),

    // ─── Public Shareable Claim Route ─────────────────────────────────────────
    GoRoute(
      path: '/claim/:token',
      builder: (context, state) {
        final token = state.pathParameters['token'] ?? '';
        return VolunteerClaimScreen(token: token);
      },
    ),
  ],
);
