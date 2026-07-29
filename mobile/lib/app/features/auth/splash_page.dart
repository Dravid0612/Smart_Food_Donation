import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/app_state.dart';
import 'login_page.dart';
import '../donor/donor_dashboard_page.dart';
import '../ngo/ngo_dashboard_page.dart';
import '../admin/admin_dashboard_page.dart';

class SplashPage extends StatefulWidget {
  const SplashPage({super.key});

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _navigate();
    });
  }

  Future<void> _navigate() async {
    final auth = context.read<AuthProvider>();
    await auth.restoreSession();
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
    } else {
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const LoginPage()));
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.food_bank_outlined, size: 72, color: Colors.green),
            SizedBox(height: 16),
            Text('Smart Food Donation', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            Text('Preparing your experience...')
          ],
        ),
      ),
    );
  }
}
