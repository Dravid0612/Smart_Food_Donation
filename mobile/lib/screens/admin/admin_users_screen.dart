import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/localization/app_locale.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/admin_provider.dart';
import '../../widgets/loading_state_widget.dart';
import '../../widgets/empty_state_widget.dart';
import '../../widgets/role_bottom_nav.dart';
import '../../models/user_model.dart';

/// Admin User Management Screen with role filters and live active/blocked status toggles.
class AdminUsersScreen extends StatefulWidget {
  const AdminUsersScreen({super.key});

  @override
  State<AdminUsersScreen> createState() => _AdminUsersScreenState();
}

class _AdminUsersScreenState extends State<AdminUsersScreen> {
  String _selectedRole = 'all';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AdminProvider>(context, listen: false).fetchAllUsers();
    });
  }

  void _showUserInspectDialog(BuildContext context, UserModel user) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.card,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusCard)),
        title: Row(
          children: [
            const Icon(Icons.person_search_outlined, color: AppTheme.primaryGreen, size: 22),
            const SizedBox(width: 8),
            Text(user.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildDetailRow('Role', user.role.toUpperCase()),
            _buildDetailRow('Email', user.email),
            _buildDetailRow('Phone', user.phone ?? 'N/A'),
            _buildDetailRow('Status', user.isActive ? 'ACTIVE' : 'DEACTIVATED'),
            if (user.role == 'volunteer') ...[
              _buildDetailRow('Vehicle', user.vehicleType),
              _buildDetailRow('Capacity', '${user.carryingCapacity} Meals'),
              _buildDetailRow('Reliability Score', '${user.reliabilityScore.toStringAsFixed(1)}%'),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(context.tr('close')),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.textSecondary)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);
    final allUsers = adminProv.allUsers;
    final filteredUsers = _selectedRole == 'all'
        ? allUsers
        : allUsers.where((u) => u.role.toLowerCase() == _selectedRole).toList();

    final roleFilters = [
      {'key': 'all', 'label': context.tr('view_all'), 'icon': Icons.people_outline},
      {'key': 'donor', 'label': context.tr('role_donor'), 'icon': Icons.storefront_outlined},
      {'key': 'ngo', 'label': context.tr('role_ngo'), 'icon': Icons.home_work_outlined},
      {'key': 'volunteer', 'label': context.tr('role_volunteer'), 'icon': Icons.directions_bike},
      {'key': 'admin', 'label': context.tr('role_admin'), 'icon': Icons.admin_panel_settings_outlined},
    ];

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(context.tr('manage_users')),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: Column(
        children: [
          // ── Filter Chips ──────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.all(AppTheme.space16),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: roleFilters.map((f) {
                  final key = f['key'] as String;
                  final isSelected = _selectedRole == key;
                  final count = key == 'all'
                      ? allUsers.length
                      : allUsers.where((u) => u.role.toLowerCase() == key).length;
                  return Padding(
                    padding: const EdgeInsets.only(right: AppTheme.space8),
                    child: ChoiceChip(
                      avatar: Icon(f['icon'] as IconData, size: 16),
                      label: Text('${f['label']} ($count)'),
                      selected: isSelected,
                      onSelected: (_) => setState(() => _selectedRole = key),
                      selectedColor: AppTheme.primaryGreen.withValues(alpha: 0.15),
                      backgroundColor: AppTheme.card,
                      side: BorderSide(color: isSelected ? AppTheme.primaryGreen : AppTheme.border),
                      labelStyle: TextStyle(
                        color: isSelected ? AppTheme.primaryGreen : AppTheme.textPrimary,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        fontSize: 12,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),

          // ── User List ─────────────────────────────────────────────────
          Expanded(
            child: adminProv.isLoading
                ? LoadingStateWidget(message: context.tr('processing'))
                : filteredUsers.isEmpty
                    ? EmptyStateWidget(
                        icon: Icons.people_outline,
                        title: context.tr('no_donations'),
                        description: context.tr('no_donations_desc'),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: AppTheme.space16),
                        itemCount: filteredUsers.length,
                        itemBuilder: (context, index) {
                          final user = filteredUsers[index];

                          return InkWell(
                            borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                            onTap: () => _showUserInspectDialog(context, user),
                            child: Container(
                              margin: const EdgeInsets.only(bottom: AppTheme.space8),
                              padding: const EdgeInsets.all(AppTheme.space12),
                              decoration: BoxDecoration(
                                color: AppTheme.card,
                                borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                                border: Border.all(color: AppTheme.border),
                              ),
                              child: Row(
                                children: [
                                  CircleAvatar(
                                    backgroundColor: user.isActive
                                        ? AppTheme.primaryGreen.withValues(alpha: 0.1)
                                        : AppTheme.error.withValues(alpha: 0.1),
                                    child: Icon(
                                      user.isActive ? Icons.person : Icons.person_off_outlined,
                                      color: user.isActive ? AppTheme.primaryGreen : AppTheme.error,
                                      size: 20,
                                    ),
                                  ),
                                  const SizedBox(width: AppTheme.space12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          user.name,
                                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.textPrimary),
                                        ),
                                        Text(
                                          user.email,
                                          style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        const SizedBox(height: 4),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: AppTheme.background,
                                            borderRadius: BorderRadius.circular(AppTheme.radiusSmall),
                                          ),
                                          child: Text(
                                            context.trRole(user.role).toUpperCase(),
                                            style: const TextStyle(
                                              color: AppTheme.textSecondary,
                                              fontSize: 10,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Switch(
                                        value: user.isActive,
                                        activeThumbColor: AppTheme.primaryGreen,
                                        onChanged: (val) async {
                                          final messenger = ScaffoldMessenger.of(context);
                                          final confirmText = context.tr('confirm');
                                          final ok = await adminProv.toggleUserActive(user.id);
                                          if (ok && mounted) {
                                            messenger.showSnackBar(
                                              SnackBar(
                                                content: Text(confirmText),
                                              ),
                                            );
                                          }
                                        },
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
      bottomNavigationBar: const RoleBottomNav(currentRole: 'admin', currentIndex: 2),
    );
  }
}
