import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/admin_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/loading_indicator.dart';

class AdminUsersScreen extends StatefulWidget {
  const AdminUsersScreen({super.key});

  @override
  State<AdminUsersScreen> createState() => _AdminUsersScreenState();
}

class _AdminUsersScreenState extends State<AdminUsersScreen> {
  String _selectedRole = 'all';

  final _roleFilters = [
    {'key': 'all', 'label': 'All', 'icon': Icons.people},
    {'key': 'donor', 'label': 'Donors', 'icon': Icons.volunteer_activism},
    {'key': 'ngo', 'label': 'NGOs', 'icon': Icons.business},
    {'key': 'volunteer', 'label': 'Volunteers', 'icon': Icons.directions_bike},
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AdminProvider>(context, listen: false).fetchAllUsers();
    });
  }

  @override
  Widget build(BuildContext context) {
    final adminProv = Provider.of<AdminProvider>(context);
    final allUsers = adminProv.allUsers;
    final filteredUsers = _selectedRole == 'all'
        ? allUsers
        : allUsers.where((u) => u.role == _selectedRole).toList();

    final roleColors = {
      'donor': const Color(0xFF10B981),
      'ngo': Colors.amber.shade700,
      'volunteer': Colors.blue,
      'admin': Colors.purple,
    };
    final roleIcons = {
      'donor': Icons.volunteer_activism,
      'ngo': Icons.business,
      'volunteer': Icons.directions_bike,
      'admin': Icons.admin_panel_settings,
    };

    return Scaffold(
      appBar: AppBar(
        title: const Text('Manage User Accounts'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: Column(
        children: [
          // ── Role Filter Chips ──────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: _roleFilters.map((f) {
                  final key = f['key'] as String;
                  final isSelected = _selectedRole == key;
                  final count = key == 'all'
                      ? allUsers.length
                      : allUsers.where((u) => u.role == key).length;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      avatar: Icon(f['icon'] as IconData, size: 16),
                      label: Text('${f['label']} ($count)'),
                      selected: isSelected,
                      onSelected: (_) => setState(() => _selectedRole = key),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 12),

          // ── User List ─────────────────────────────────────────────────
          Expanded(
            child: adminProv.isLoading
                ? const LoadingIndicatorWidget(message: 'Fetching platform users...')
                : filteredUsers.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.people_outline, size: 48, color: Colors.grey),
                            const SizedBox(height: 12),
                            Text('No ${_selectedRole == 'all' ? '' : _selectedRole} users found.',
                                style: const TextStyle(color: Colors.grey)),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        itemCount: filteredUsers.length,
                        itemBuilder: (context, index) {
                          final user = filteredUsers[index];
                          final roleColor = roleColors[user.role] ?? Colors.grey;
                          final roleIcon = roleIcons[user.role] ?? Icons.person;

                          return CustomCard(
                            child: Row(
                              children: [
                                CircleAvatar(
                                  backgroundColor: user.isActive
                                      ? roleColor.withOpacity(0.15)
                                      : Colors.red.shade50,
                                  child: Icon(
                                    user.isActive ? roleIcon : Icons.person_off,
                                    color: user.isActive ? roleColor : Colors.redAccent,
                                    size: 22,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(user.name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                                      Text(user.email, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)), overflow: TextOverflow.ellipsis),
                                      const SizedBox(height: 4),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: roleColor.withOpacity(0.1),
                                          borderRadius: BorderRadius.circular(12),
                                        ),
                                        child: Text(
                                          user.role.toUpperCase(),
                                          style: TextStyle(color: roleColor, fontSize: 10, fontWeight: FontWeight.bold),
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
                                      activeColor: const Color(0xFF10B981),
                                      onChanged: (val) async {
                                        final ok = await adminProv.toggleUserActive(user.id);
                                        if (ok && mounted) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            SnackBar(
                                              content: Text(user.isActive
                                                  ? '${user.name} blocked.'
                                                  : '${user.name} unblocked.'),
                                            ),
                                          );
                                        }
                                      },
                                    ),
                                    Text(
                                      user.isActive ? 'Active' : 'Blocked',
                                      style: TextStyle(
                                        fontSize: 10,
                                        color: user.isActive ? const Color(0xFF10B981) : Colors.redAccent,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
