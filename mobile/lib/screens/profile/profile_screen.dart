import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../models/user_model.dart';
import '../../models/ngo_model.dart';
import '../../providers/auth_provider.dart';
import '../../providers/volunteer_task_provider.dart';
import '../../providers/ngo_provider.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/role_bottom_nav.dart';

/// App-wide Profile Screen supporting all 4 roles:
/// - Food Donor: Meals contributed, CO2 savings, CSR certificate & recurring schedules
/// - Partner NGO: Daily intake capacity, distribution logging, operating hours
/// - Volunteer Hero: Live availability toggle, reliability rating, vehicle capacity
/// - Administrator: Hungarian matchmaking, NGO verification, user RBAC & audit console
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _volunteerAvailable = true;

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final localeProv = Provider.of<LocaleProvider>(context);
    final user = auth.currentUser;
    final role = (user?.role ?? 'donor').toLowerCase();

    NgoProvider? ngoProv;
    try {
      ngoProv = Provider.of<NgoProvider>(context, listen: false);
    } catch (_) {}
    final myNgo = (role == 'ngo') ? ngoProv?.myNgo : null;

    // Semantic colors & assets per role
    final Color roleColor;
    final Color roleBgColor;
    final IconData roleIcon;
    final String roleTitle;

    switch (role) {
      case 'ngo':
        roleColor = const Color(0xFFD97706); // Amber / Terracotta
        roleBgColor = const Color(0xFFFEF3C7);
        roleIcon = Icons.home_work_rounded;
        roleTitle = context.trRole('ngo');
        break;
      case 'volunteer':
        roleColor = const Color(0xFF0284C7); // Ocean Blue
        roleBgColor = const Color(0xFFE0F2FE);
        roleIcon = Icons.two_wheeler_rounded;
        roleTitle = context.trRole('volunteer');
        break;
      case 'admin':
        roleColor = const Color(0xFF7C3AED); // Royal Purple
        roleBgColor = const Color(0xFFF3E8FF);
        roleIcon = Icons.admin_panel_settings_rounded;
        roleTitle = context.trRole('admin');
        break;
      case 'donor':
      default:
        roleColor = AppTheme.primaryGreen;
        roleBgColor = AppTheme.primaryGreen.withValues(alpha: 0.12);
        roleIcon = Icons.restaurant_rounded;
        roleTitle = context.trRole('donor');
        break;
    }

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('nav_profile'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            if (context.canPop()) {
              context.pop();
            } else {
              switch (role) {
                case 'ngo':
                  context.go('/ngo');
                  break;
                case 'volunteer':
                  context.go('/volunteer');
                  break;
                case 'admin':
                  context.go('/admin');
                  break;
                default:
                  context.go('/donor');
                  break;
              }
            }
          },
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: AppTheme.error),
            tooltip: context.tr('logout'),
            onPressed: () => _confirmLogout(context, auth),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16, vertical: AppTheme.space12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── 1. ROLE HERO PROFILE CARD ──────────────────────────────────
            _buildHeroProfileCard(context, user, role, roleColor, roleBgColor, roleIcon, roleTitle, myNgo: myNgo),
            const SizedBox(height: AppTheme.space16),

            // ── 2. ROLE-SPECIFIC 2x2 METRICS OVERVIEW ──────────────────────
            _buildRoleMetricsGrid(context, user, role, roleColor, myNgo: myNgo),
            const SizedBox(height: AppTheme.space16),

            // ── 3. ROLE-SPECIFIC QUICK ACTIONS & MANAGEMENT ────────────────
            _buildRoleQuickActions(context, role, roleColor),
            const SizedBox(height: AppTheme.space16),

            // ── 4. APP LANGUAGE SELECTOR ────────────────────────────────────
            _buildLanguageCard(context, localeProv),
            const SizedBox(height: AppTheme.space16),

            // ── 5. CONTACT & FACILITY INFO ──────────────────────────────────
            _buildContactInfoCard(context, user, roleColor, myNgo: myNgo),
            const SizedBox(height: AppTheme.space20),

            // ── 6. LOGOUT BUTTON & FOOTER ───────────────────────────────────
            _buildLogoutSection(context, auth),
            const SizedBox(height: AppTheme.space24),
          ],
        ),
      ),
      bottomNavigationBar: RoleBottomNav(
        currentRole: role,
        currentIndex: role == 'admin' ? 4 : (role == 'donor' ? 3 : 2),
      ),
    );
  }

  // ── 1. HERO PROFILE CARD ──────────────────────────────────────────────────
  Widget _buildHeroProfileCard(
    BuildContext context,
    dynamic user,
    String role,
    Color roleColor,
    Color roleBgColor,
    IconData roleIcon,
    String roleTitle, {
    dynamic myNgo,
  }) {
    String trustBadgeText = '';
    IconData trustIcon = Icons.verified_user_rounded;

    if (role == 'donor') {
      trustBadgeText = '${context.tr('fssai_certified')} • ${context.tr('verified_partner')}';
      trustIcon = Icons.workspace_premium_rounded;
    } else if (role == 'ngo') {
      final isVerified = myNgo?.isVerified ?? true;
      trustBadgeText = isVerified ? '${context.tr('verified')} NGO Partner • Active' : 'Verification Pending';
      trustIcon = isVerified ? Icons.verified_rounded : Icons.hourglass_top_rounded;
    } else if (role == 'volunteer') {
      trustBadgeText = '⭐ 98% ${context.tr('reliability_score')} • ${context.tr('role_volunteer')}';
      trustIcon = Icons.electric_bolt_rounded;
    } else {
      trustBadgeText = '⚡ Superadmin Governance • Operations Dispatch';
      trustIcon = Icons.shield_rounded;
    }

    return Container(
      padding: const EdgeInsets.all(AppTheme.space20),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        children: [
          // Avatar with colored ring
          Stack(
            alignment: Alignment.bottomRight,
            children: [
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: roleColor.withValues(alpha: 0.6), width: 3),
                ),
                child: CircleAvatar(
                  radius: 40,
                  backgroundColor: roleColor,
                  child: Icon(roleIcon, size: 40, color: Colors.white),
                ),
              ),
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(color: Colors.black.withValues(alpha: 0.1), blurRadius: 4),
                  ],
                ),
                child: Icon(Icons.check_circle_rounded, color: roleColor, size: 20),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space12),

          // User / Organization Name
          Text(
            (role == 'ngo' && myNgo?.organizationName != null && myNgo!.organizationName.isNotEmpty)
                ? myNgo!.organizationName
                : (user?.name ?? 'Smart Food Partner'),
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: AppTheme.textPrimary,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: AppTheme.space6),

          // Role Badge Pill
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
            decoration: BoxDecoration(
              color: roleBgColor,
              borderRadius: BorderRadius.circular(AppTheme.radiusPill),
              border: Border.all(color: roleColor.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(roleIcon, size: 14, color: roleColor),
                const SizedBox(width: 6),
                Text(
                  roleTitle,
                  style: TextStyle(
                    color: roleColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppTheme.space10),

          // Trust Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.background,
              borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(trustIcon, color: roleColor, size: 15),
                const SizedBox(width: 6),
                Text(
                  trustBadgeText,
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── 2. 2x2 METRICS GRID PER ROLE ───────────────────────────────────────────
  Widget _buildRoleMetricsGrid(BuildContext context, dynamic user, String role, Color roleColor, {dynamic myNgo}) {
    final List<Map<String, dynamic>> metrics;

    if (role == 'donor') {
      final meals = (user?.totalMealsDonated ?? 420).toInt();
      final co2 = (meals * 0.45).toStringAsFixed(1);
      metrics = [
        {'label': context.tr('meals_donated_count'), 'val': '$meals', 'sub': context.tr('unit_meals'), 'icon': Icons.restaurant_rounded},
        {'label': context.tr('co2_diverted'), 'val': '$co2', 'sub': 'kg CO₂e', 'icon': Icons.eco_rounded},
        {'label': context.tr('trust_score'), 'val': '5.0 ★', 'sub': context.tr('verified_partner'), 'icon': Icons.verified_user_rounded},
        {'label': 'CSR Tier', 'val': 'Gold', 'sub': 'Top 5% Partner', 'icon': Icons.workspace_premium_rounded},
      ];
    } else if (role == 'ngo') {
      final capacity = (myNgo?.capacity ?? (user?.carryingCapacity ?? 150)).toInt();
      metrics = [
        {'label': context.tr('intake_capacity'), 'val': '$capacity', 'sub': '${context.tr('unit_meals')}/day', 'icon': Icons.inventory_2_rounded},
        {'label': context.tr('meals_distributed'), 'val': '1,280', 'sub': context.tr('status_completed'), 'icon': Icons.volunteer_activism_rounded},
        {'label': 'Beneficiary Units', 'val': '3 Centers', 'sub': 'Verified Shelters', 'icon': Icons.maps_home_work_rounded},
        {'label': 'Safety Standard', 'val': 'FSSAI OK', 'sub': 'Hygienic Transit', 'icon': Icons.health_and_safety_rounded},
      ];
    } else if (role == 'volunteer') {
      final reliability = (user?.reliabilityScore ?? 98.0).toInt();
      final capacity = (user?.carryingCapacity ?? 50).toInt();
      final vehicle = (user?.vehicleType ?? 'Bike').toString().toUpperCase();
      metrics = [
        {'label': context.tr('reliability_score'), 'val': '$reliability%', 'sub': '4.9 ★ Rating', 'icon': Icons.star_rounded},
        {'label': context.tr('missions_completed'), 'val': '38', 'sub': 'Safe Handover', 'icon': Icons.verified_rounded},
        {'label': context.tr('carrying_capacity'), 'val': '$capacity', 'sub': context.tr('unit_meals'), 'icon': Icons.local_shipping_rounded},
        {'label': context.tr('vehicle_type'), 'val': vehicle, 'sub': 'Insulated Box', 'icon': Icons.two_wheeler_rounded},
      ];
    } else {
      // Admin
      metrics = [
        {'label': 'Matchmaking', 'val': 'Active', 'sub': 'Hungarian Algo', 'icon': Icons.bolt_rounded},
        {'label': 'Verified Network', 'val': '12 NGOs', 'sub': '24 Donors', 'icon': Icons.hub_rounded},
        {'label': 'Interventions', 'val': '0 Pending', 'sub': '100% SLA Maintained', 'icon': Icons.check_circle_outline_rounded},
        {'label': 'Security Guard', 'val': 'OTP Lock', 'sub': 'Strict FSM Active', 'icon': Icons.security_rounded},
      ];
    }

    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.insights_rounded, color: roleColor, size: 18),
              const SizedBox(width: 8),
              Text(
                context.tr('key_stats'),
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space14),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: metrics.length,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 1.6,
            ),
            itemBuilder: (ctx, idx) {
              final m = metrics[idx];
              return Container(
                padding: const EdgeInsets.all(AppTheme.space10),
                decoration: BoxDecoration(
                  color: AppTheme.background,
                  borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
                  border: Border.all(color: AppTheme.border.withValues(alpha: 0.8)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            m['label'],
                            style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.w600),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Icon(m['icon'], size: 16, color: roleColor),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      m['val'],
                      style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: roleColor),
                    ),
                    Text(
                      m['sub'],
                      style: const TextStyle(fontSize: 10, color: AppTheme.textMuted, fontWeight: FontWeight.w500),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  // ── 3. QUICK ACTIONS PER ROLE ──────────────────────────────────────────────
  Widget _buildRoleQuickActions(BuildContext context, String role, Color roleColor) {
    final user = Provider.of<AuthProvider>(context, listen: false).currentUser;
    final List<Widget> actionTiles = [];

    if (role == 'donor') {
      actionTiles.addAll([
        _buildActionTile(
          icon: Icons.workspace_premium_rounded,
          color: AppTheme.primaryGreen,
          title: context.tr('view_certificate'),
          subtitle: context.tr('csr_report'),
          onTap: () => context.push('/donor/certificate'),
        ),
        _buildActionTile(
          icon: Icons.repeat_rounded,
          color: const Color(0xFF0284C7),
          title: context.tr('recurring_donations'),
          subtitle: 'Automate surplus food schedules',
          onTap: () => context.push('/donor/recurring'),
        ),
        _buildActionTile(
          icon: Icons.health_and_safety_rounded,
          color: const Color(0xFFD97706),
          title: context.tr('fssai_guidelines'),
          subtitle: 'Surplus food compliance & hygiene',
          onTap: () => _showFssaiModal(context),
        ),
        _buildActionTile(
          icon: Icons.help_outline_rounded,
          color: const Color(0xFF7C3AED),
          title: context.tr('why_donate'),
          subtitle: 'Zero hunger & CSR tax incentives',
          onTap: () => context.push('/donor/why-donate'),
        ),
      ]);
    } else if (role == 'ngo') {
      actionTiles.addAll([
        _buildActionTile(
          icon: Icons.inventory_rounded,
          color: const Color(0xFFD97706),
          title: context.tr('record_distribution_btn'),
          subtitle: 'Log meals served to shelter beneficiaries',
          onTap: () => context.go('/ngo'),
        ),
        _buildActionTile(
          icon: Icons.checklist_rounded,
          color: AppTheme.primaryGreen,
          title: context.tr('nav_requirements'),
          subtitle: 'Update daily intake capacity & demands',
          onTap: () => context.push('/ngo/requirements'),
        ),
        _buildActionTile(
          icon: Icons.schedule_rounded,
          color: const Color(0xFF0284C7),
          title: context.tr('operating_hours'),
          subtitle: 'Receiving hours: 8:00 AM - 10:00 PM',
          onTap: () => _showOperatingHoursModal(context),
        ),
      ]);
    } else if (role == 'volunteer') {
      actionTiles.addAll([
        Container(
          padding: const EdgeInsets.symmetric(horizontal: AppTheme.space14, vertical: AppTheme.space10),
          decoration: BoxDecoration(
            color: AppTheme.background,
            borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
            border: Border.all(color: AppTheme.border),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: (_volunteerAvailable ? AppTheme.primaryGreen : AppTheme.textMuted).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                    ),
                    child: Icon(
                      _volunteerAvailable ? Icons.check_circle_rounded : Icons.pause_circle_rounded,
                      color: _volunteerAvailable ? AppTheme.primaryGreen : AppTheme.textMuted,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.tr('availability_status'),
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.textPrimary),
                      ),
                      Text(
                        _volunteerAvailable ? 'Online • Ready for dispatch' : 'Offline • Duty paused',
                        style: TextStyle(
                          fontSize: 11,
                          color: _volunteerAvailable ? AppTheme.primaryGreen : AppTheme.textMuted,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              Switch(
                value: _volunteerAvailable,
                activeThumbColor: AppTheme.primaryGreen,
                onChanged: (val) {
                  setState(() => _volunteerAvailable = val);
                  final prov = Provider.of<VolunteerTaskProvider>(context, listen: false);
                  prov.setAvailability(val);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(val ? '🟢 Courier is now ONLINE and ready for dispatch.' : '⚪ Courier is now OFFLINE.'),
                      backgroundColor: val ? AppTheme.primaryGreen : AppTheme.textSecondary,
                      duration: const Duration(seconds: 2),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        _buildActionTile(
          icon: Icons.two_wheeler_rounded,
          color: const Color(0xFF0284C7),
          title: context.tr('vehicle_profile'),
          subtitle: '${user?.vehicleType ?? "Bike"} • ${user?.carryingCapacity ?? 50} ${context.tr("meals")}',
          onTap: () => context.push('/volunteer/vehicle'),
        ),
        _buildActionTile(
          icon: Icons.two_wheeler_rounded,
          color: const Color(0xFF0284C7),
          title: context.tr('active_rescues'),
          subtitle: 'Active pick-up missions & route map',
          onTap: () => context.go('/volunteer'),
        ),
        _buildActionTile(
          icon: Icons.emergency_rounded,
          color: AppTheme.error,
          title: context.tr('emergency_escalation'),
          subtitle: '24/7 Operations Control Support',
          onTap: () => _showEmergencyHotlineModal(context),
        ),
      ]);
    } else {
      // Admin
      actionTiles.addAll([
        _buildActionTile(
          icon: Icons.verified_user_rounded,
          color: const Color(0xFF7C3AED),
          title: context.tr('verify_ngos'),
          subtitle: 'Review NGO registration & 80G documents',
          onTap: () => context.push('/admin/ngos'),
        ),
        _buildActionTile(
          icon: Icons.manage_accounts_rounded,
          color: const Color(0xFF0284C7),
          title: context.tr('manage_users'),
          subtitle: 'Role permissions & account suspension',
          onTap: () => context.push('/admin/users'),
        ),
        _buildActionTile(
          icon: Icons.gavel_rounded,
          color: const Color(0xFFD97706),
          title: context.tr('dispute_resolution'),
          subtitle: 'Resolve transit issues & claims',
          onTap: () => context.push('/admin/disputes'),
        ),
        _buildActionTile(
          icon: Icons.bolt_rounded,
          color: AppTheme.primaryGreen,
          title: context.tr('system_interventions'),
          subtitle: 'Hungarian dispatch & fallback escalation',
          onTap: () => context.push('/admin/interventions'),
        ),
      ]);
    }

    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.dashboard_customize_rounded, color: roleColor, size: 18),
              const SizedBox(width: 8),
              Text(
                context.tr('quick_services'),
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space12),
          ...actionTiles,
        ],
      ),
    );
  }

  Widget _buildActionTile({
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: AppTheme.background,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: AppTheme.border),
          borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
        ),
        child: ListTile(
          onTap: onTap,
          dense: true,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusMedium)),
          leading: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
            ),
            child: Icon(icon, color: color, size: 18),
          ),
          title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.textPrimary)),
          subtitle: Text(subtitle, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
          trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppTheme.textMuted),
        ),
      ),
    );
  }

  // ── 4. APP LANGUAGE SELECTOR ───────────────────────────────────────────────
  Widget _buildLanguageCard(BuildContext context, LocaleProvider prov) {
    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.translate_rounded, color: AppTheme.primaryGreen, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${context.tr('app_language')} / மொழி / भाषा',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space12),
          Row(
            children: [
              _buildLangChoice(context, prov, 'en', 'English', 'EN'),
              const SizedBox(width: 8),
              _buildLangChoice(context, prov, 'ta', 'தமிழ்', 'TA'),
              const SizedBox(width: 8),
              _buildLangChoice(context, prov, 'hi', 'हिन्दी', 'HI'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLangChoice(BuildContext context, LocaleProvider prov, String code, String label, String sub) {
    final isSelected = prov.currentLanguage == code;
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
        onTap: () {
          prov.setLanguage(code);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(context.tr('language_updated')),
              duration: const Duration(seconds: 1),
              backgroundColor: AppTheme.primaryGreen,
            ),
          );
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
          decoration: BoxDecoration(
            color: isSelected ? AppTheme.primaryGreen : AppTheme.background,
            borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
            border: Border.all(
              color: isSelected ? AppTheme.primaryGreen : AppTheme.border,
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      color: isSelected ? Colors.white : AppTheme.textPrimary,
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                  if (isSelected) ...[
                    const SizedBox(width: 4),
                    const Icon(Icons.check_rounded, color: Colors.white, size: 14),
                  ],
                ],
              ),
              const SizedBox(height: 2),
              Text(
                sub,
                style: TextStyle(
                  color: isSelected ? Colors.white70 : AppTheme.textMuted,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── 5. CONTACT & FACILITY INFO ─────────────────────────────────────────────
  Widget _buildContactInfoCard(BuildContext context, UserModel? user, Color roleColor, {NgoModel? myNgo}) {
    final role = (user?.role ?? 'donor').toString().toLowerCase();
    final phone = (role == 'ngo' && myNgo?.contactPhone != null && myNgo!.contactPhone!.isNotEmpty)
        ? myNgo.contactPhone!
        : (user?.phone ?? '+91 98765 43210');
    final address = (role == 'ngo' && myNgo?.address != null && myNgo!.address!.isNotEmpty)
        ? myNgo.address!
        : (user?.address ?? 'MG Road, Bangalore, India');

    return Container(
      padding: const EdgeInsets.all(AppTheme.space16),
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppTheme.radiusCard),
        border: Border.all(color: AppTheme.border),
        boxShadow: AppTheme.shadowCard,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.badge_rounded, color: roleColor, size: 18),
              const SizedBox(width: 8),
              Text(
                context.tr('contact_details'),
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textPrimary),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space12),
          _buildInfoRow(Icons.email_outlined, context.tr('email'), user?.email ?? 'support@smartfood.org'),
          const Divider(height: 16),
          _buildInfoRow(Icons.phone_outlined, context.tr('phone_number'), phone),
          const Divider(height: 16),
          _buildInfoRow(Icons.location_on_outlined, context.tr('address'), address),
          if (role == 'volunteer') ...[
            const Divider(height: 16),
            _buildInfoRow(Icons.two_wheeler_outlined, context.tr('vehicle_type'), (user?.vehicleType ?? 'Bike').toUpperCase()),
            const Divider(height: 16),
            _buildInfoRow(Icons.fitness_center_outlined, context.tr('carrying_capacity'), '${user?.carryingCapacity ?? 50} ${context.tr('meals')}'),
          ],
        ],
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: AppTheme.background,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Icon(icon, color: AppTheme.textSecondary, size: 16),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontWeight: FontWeight.w500)),
              const SizedBox(height: 2),
              Text(value, style: const TextStyle(fontSize: 13, color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
            ],
          ),
        ),
      ],
    );
  }

  // ── 6. LOGOUT & FOOTER ─────────────────────────────────────────────────────
  Widget _buildLogoutSection(BuildContext context, AuthProvider auth) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          height: 48,
          child: OutlinedButton.icon(
            onPressed: () => _confirmLogout(context, auth),
            icon: const Icon(Icons.logout_rounded, color: AppTheme.error, size: 18),
            label: Text(
              context.tr('logout'),
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.error),
            ),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: AppTheme.error, width: 1.5),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusButton)),
            ),
          ),
        ),
        const SizedBox(height: AppTheme.space14),
        const Text(
          'Smart Food Rescue Platform v2.4.0\nZero Hunger & Zero Food Waste Network',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.4),
        ),
      ],
    );
  }

  Future<void> _confirmLogout(BuildContext context, AuthProvider auth) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.card,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusFeatureCard)),
        title: Row(
          children: [
            const Icon(Icons.logout_rounded, color: AppTheme.error),
            const SizedBox(width: 8),
            Text(ctx.tr('logout'), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          ],
        ),
        content: Text(ctx.tr('logout_confirm'), style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(ctx.tr('cancel'), style: const TextStyle(color: AppTheme.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
            child: Text(ctx.tr('logout'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );

    if (confirm == true && context.mounted) {
      await auth.logout();
      if (context.mounted) {
        context.go('/login');
      }
    }
  }

  // ── MODALS FOR GUIDELINES & SUPPORT ────────────────────────────────────────
  void _showFssaiModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.card,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusFeatureCard)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(AppTheme.space24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.health_and_safety_rounded, color: AppTheme.primaryGreen, size: 24),
                SizedBox(width: 8),
                Text('FSSAI Food Safety Compliance', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
              ],
            ),
            const SizedBox(height: AppTheme.space12),
            const Text(
              'Under FSSAI Surplus Food Regulations, food donors must ensure:\n'
              '1. Food is prepared in hygienic conditions.\n'
              '2. Maximum 4 hours storage at room temperature or continuous refrigeration (<5°C).\n'
              '3. Proper covered/sealed packaging to prevent contamination during transit.\n'
              '4. Accurate declaration of preparation time and food allergens.',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.5),
            ),
            const SizedBox(height: AppTheme.space20),
            SizedBox(
              width: double.infinity,
              height: 44,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(ctx),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryGreen),
                child: const Text('I Understand & Comply', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showOperatingHoursModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.card,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusFeatureCard)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(AppTheme.space24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('NGO Operating & Intake Hours', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
            const SizedBox(height: AppTheme.space12),
            const Text(
              '• Morning Intake: 8:00 AM - 12:00 PM\n'
              '• Afternoon Intake: 1:00 PM - 5:00 PM\n'
              '• Evening Rescue Window: 6:00 PM - 10:00 PM\n\n'
              'Emergency after-hours deliveries are coordinated through the Admin Operations Console.',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.5),
            ),
            const SizedBox(height: AppTheme.space20),
            SizedBox(
              width: double.infinity,
              height: 44,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(ctx),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFD97706)),
                child: const Text('Close', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showEmergencyHotlineModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.card,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusFeatureCard)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(AppTheme.space24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.emergency_rounded, color: AppTheme.error, size: 24),
                SizedBox(width: 8),
                Text('Emergency Courier Support', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
              ],
            ),
            const SizedBox(height: AppTheme.space12),
            const Text(
              'In case of accident, vehicle breakdown, donor unreachability, or spill during transit:\n\n'
              '📞 Operations Hotline: +91 1800-425-FOOD\n'
              '✉️ Emergency Dispatch: dispatch@smartfood.org\n\n'
              'You can also report a transit problem directly from the active mission screen to trigger immediate fallback rerouting.',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13, height: 1.5),
            ),
            const SizedBox(height: AppTheme.space20),
            SizedBox(
              width: double.infinity,
              height: 44,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(ctx),
                style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
                child: const Text('Got It', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
