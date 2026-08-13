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
    final users = adminProv.allUsers;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Manage User Accounts'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: adminProv.isLoading
          ? const LoadingIndicatorWidget(message: 'Fetching platform users...')
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: users.length,
              itemBuilder: (context, index) {
                final user = users[index];
                return CustomCard(
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: user.isActive ? const Color(0xFFD1FAE5) : Colors.red.shade100,
                      child: Icon(
                        user.isActive ? Icons.person : Icons.person_off,
                        color: user.isActive ? const Color(0xFF10B981) : Colors.red,
                      ),
                    ),
                    title: Text(user.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text('${user.email} • Role: ${user.role.toUpperCase()}'),
                    trailing: Switch(
                      value: user.isActive,
                      activeColor: const Color(0xFF10B981),
                      onChanged: (val) async {
                        final ok = await adminProv.toggleUserActive(user.id);
                        if (ok && mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text('Account status updated for ${user.name}'),
                            ),
                          );
                        }
                      },
                    ),
                  ),
                );
              },
            ),
    );
  }
}
