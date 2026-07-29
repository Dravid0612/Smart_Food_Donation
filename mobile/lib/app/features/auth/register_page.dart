import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_state.dart';
import '../donor/donor_dashboard_page.dart';
import '../ngo/ngo_dashboard_page.dart';
import '../admin/admin_dashboard_page.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key});

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  String _selectedRole = 'donor';

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              TextField(controller: _nameController, decoration: const InputDecoration(labelText: 'Full name')),
              const SizedBox(height: 12),
              TextField(controller: _emailController, decoration: const InputDecoration(labelText: 'Email')),
              const SizedBox(height: 12),
              TextField(controller: _passwordController, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _selectedRole,
                items: const [
                  DropdownMenuItem(value: 'donor', child: Text('Donor')),
                  DropdownMenuItem(value: 'ngo', child: Text('NGO')),
                  DropdownMenuItem(value: 'admin', child: Text('Admin')),
                ],
                onChanged: (value) => setState(() => _selectedRole = value ?? 'donor'),
                decoration: const InputDecoration(labelText: 'Role'),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: auth.isLoading
                      ? null
                      : () async {
                          await auth.register(_nameController.text, _emailController.text, _passwordController.text, _selectedRole);
                          if (!mounted) return;
                          if (auth.isAuthenticated) {
                            switch (auth.role) {
                              case 'ngo':
                                Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const NgoDashboardPage()));
                                break;
                              case 'admin':
                                Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const AdminDashboardPage()));
                                break;
                              default:
                                Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const DonorDashboardPage()));
                            }
                          } else if (auth.errorMessage != null) {
                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(auth.errorMessage!)));
                          }
                        },
                  child: auth.isLoading ? const CircularProgressIndicator() : const Text('Register'),
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}
