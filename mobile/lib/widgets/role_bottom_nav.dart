import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../core/localization/app_locale.dart';

class RoleBottomNav extends StatelessWidget {
  final String currentRole; // donor, ngo, volunteer, admin
  final int currentIndex;

  const RoleBottomNav({
    super.key,
    required this.currentRole,
    required this.currentIndex,
  });

  @override
  Widget build(BuildContext context) {
    switch (currentRole.toLowerCase()) {
      case 'ngo':
        return NavigationBar(
          selectedIndex: currentIndex,
          onDestinationSelected: (index) {
            if (index == currentIndex) return;
            switch (index) {
              case 0:
                context.go('/ngo');
                break;
              case 1:
                context.push('/ngo/requirements');
                break;
              case 2:
                context.push('/profile');
                break;
            }
          },
          destinations: [
            NavigationDestination(
              icon: const Icon(Icons.dashboard_outlined),
              selectedIcon: const Icon(Icons.dashboard),
              label: context.tr('nav_dashboard'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.tune_outlined),
              selectedIcon: const Icon(Icons.tune),
              label: context.tr('nav_requirements'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.person_outline),
              selectedIcon: const Icon(Icons.person),
              label: context.tr('nav_profile'),
            ),
          ],
        );

      case 'volunteer':
        return NavigationBar(
          selectedIndex: currentIndex,
          onDestinationSelected: (index) {
            if (index == currentIndex) return;
            switch (index) {
              case 0:
                context.go('/volunteer');
                break;
              case 1:
                context.push('/volunteer/impact');
                break;
              case 2:
                context.push('/profile');
                break;
            }
          },
          destinations: [
            NavigationDestination(
              icon: const Icon(Icons.two_wheeler_outlined),
              selectedIcon: const Icon(Icons.two_wheeler),
              label: context.tr('nav_tasks'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.emoji_events_outlined),
              selectedIcon: const Icon(Icons.emoji_events),
              label: context.tr('nav_impact'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.person_outline),
              selectedIcon: const Icon(Icons.person),
              label: context.tr('nav_profile'),
            ),
          ],
        );

      case 'admin':
        return NavigationBar(
          selectedIndex: currentIndex,
          onDestinationSelected: (index) {
            if (index == currentIndex) return;
            switch (index) {
              case 0:
                context.go('/admin');
                break;
              case 1:
                context.go('/admin/donations');
                break;
              case 2:
                context.go('/admin/users');
                break;
              case 3:
                context.push('/admin/verify-ngos');
                break;
              case 4:
                context.push('/profile');
                break;
            }
          },
          destinations: [
            NavigationDestination(
              icon: const Icon(Icons.dashboard_outlined),
              selectedIcon: const Icon(Icons.dashboard),
              label: context.tr('nav_overview'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.local_shipping_outlined),
              selectedIcon: const Icon(Icons.local_shipping),
              label: context.tr('nav_donations'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.people_alt_outlined),
              selectedIcon: const Icon(Icons.people_alt),
              label: context.tr('nav_users'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.verified_outlined),
              selectedIcon: const Icon(Icons.verified),
              label: context.tr('verify_ngos'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.person_outline),
              selectedIcon: const Icon(Icons.person),
              label: context.tr('nav_profile'),
            ),
          ],
        );

      case 'donor':
      default:
        return NavigationBar(
          selectedIndex: currentIndex,
          onDestinationSelected: (index) {
            if (index == currentIndex) return;
            switch (index) {
              case 0:
                context.go('/donor');
                break;
              case 1:
                context.push('/donor/create');
                break;
              case 2:
                context.go('/donor/history');
                break;
              case 3:
                context.push('/profile');
                break;
            }
          },
          destinations: [
            NavigationDestination(
              icon: const Icon(Icons.home_outlined),
              selectedIcon: const Icon(Icons.home),
              label: context.tr('nav_home'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.add_circle_outline),
              selectedIcon: const Icon(Icons.add_circle),
              label: context.tr('nav_donate'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.history_outlined),
              selectedIcon: const Icon(Icons.history),
              label: context.tr('nav_history'),
            ),
            NavigationDestination(
              icon: const Icon(Icons.person_outline),
              selectedIcon: const Icon(Icons.person),
              label: context.tr('nav_profile'),
            ),
          ],
        );
    }
  }
}
