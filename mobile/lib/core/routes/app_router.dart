import 'package:go_router/go_router.dart';
import '../../screens/splash/splash_screen.dart';
import '../../screens/onboarding/onboarding_screen.dart';
import '../../screens/auth/login_screen.dart';
import '../../screens/auth/register_screen.dart';

// Donor
import '../../screens/donor/donor_dashboard.dart';
import '../../screens/donor/create_donation_screen.dart';
import '../../screens/donor/donation_detail_screen.dart';
import '../../screens/donor/donor_rewards_screen.dart';
import '../../screens/donor/donor_ai_analysis_screen.dart';

// NGO
import '../../screens/ngo/ngo_dashboard.dart';
import '../../screens/ngo/ngo_food_requirements_screen.dart';
import '../../screens/ngo/ngo_receiving_screen.dart';
import '../../screens/ngo/ngo_distribution_screen.dart';

// Volunteer
import '../../screens/volunteer/volunteer_dashboard.dart';
import '../../screens/volunteer/volunteer_pickup_request_screen.dart';
import '../../screens/volunteer/volunteer_active_task_screen.dart';
import '../../screens/volunteer/volunteer_impact_screen.dart';

// Admin
import '../../screens/admin/admin_dashboard.dart';
import '../../screens/admin/admin_users_screen.dart';
import '../../screens/admin/ngo_verification_screen.dart';

// Shared
import '../../screens/notifications/notification_center_screen.dart';
import '../../screens/profile/profile_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const SplashScreen()),
    GoRoute(path: '/onboarding', builder: (context, state) => const OnboardingScreen()),
    GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
    GoRoute(path: '/register', builder: (context, state) => const RegisterScreen()),

    // ─── Donor Routes ───────────────────────────────────────────────────────
    GoRoute(path: '/donor', builder: (context, state) => const DonorDashboardScreen()),
    GoRoute(path: '/donor/create', builder: (context, state) => const CreateDonationScreen()),
    GoRoute(
      path: '/donor/detail/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return DonationDetailScreen(donationId: id);
      },
    ),
    GoRoute(path: '/donor/rewards', builder: (context, state) => const DonorRewardsScreen()),
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
    GoRoute(
      path: '/ngo/receiving/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return NgoReceivingScreen(donationId: id);
      },
    ),
    GoRoute(
      path: '/ngo/distribution/:id',
      builder: (context, state) {
        final id = int.parse(state.pathParameters['id'] ?? '1');
        return NgoDistributionScreen(donationId: id);
      },
    ),

    // ─── Volunteer Routes ────────────────────────────────────────────────────
    GoRoute(path: '/volunteer', builder: (context, state) => const VolunteerDashboardScreen()),
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
    GoRoute(path: '/admin/users', builder: (context, state) => const AdminUsersScreen()),
    GoRoute(path: '/admin/verify-ngos', builder: (context, state) => const NgoVerificationScreen()),

    // ─── Shared Routes ───────────────────────────────────────────────────────
    GoRoute(path: '/notifications', builder: (context, state) => const NotificationCenterScreen()),
    GoRoute(path: '/profile', builder: (context, state) => const ProfileScreen()),
  ],
);
