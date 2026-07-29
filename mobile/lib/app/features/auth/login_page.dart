import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_state.dart';
import 'register_page.dart';
import '../donor/donor_dashboard_page.dart';
import '../ngo/ngo_dashboard_page.dart';
import '../admin/admin_dashboard_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                const Icon(Icons.volunteer_activism, size: 72, color: Colors.green),
                const SizedBox(height: 16),
                const Text('Welcome back', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                const Text('Sign in to continue helping your community', textAlign: TextAlign.center),
                const SizedBox(height: 24),
                TextField(controller: _emailController, decoration: const InputDecoration(labelText: 'Email')),
                const SizedBox(height: 12),
                TextField(controller: _passwordController, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: auth.isLoading
                        ? null
                        : () async {
                            await auth.login(_emailController.text, _passwordController.text);
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
                    child: auth.isLoading ? const CircularProgressIndicator() : const Text('Login'),
                  ),
                ),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RegisterPage())),
                  child: const Text('Create account'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
