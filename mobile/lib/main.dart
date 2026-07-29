import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'app/core/app_state.dart';
import 'app/core/api_service.dart';
import 'app/theme/app_theme.dart';
import 'app/features/auth/splash_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final apiService = ApiService();
  runApp(
    MultiProvider(
      providers: [
        Provider.value(value: apiService),
        ChangeNotifierProvider(create: (_) => AuthProvider(apiService: apiService)),
        ChangeNotifierProvider(create: (_) => DonationProvider(apiService: apiService)),
      ],
      child: const SmartFoodApp(),
    ),
  );
}

class SmartFoodApp extends StatelessWidget {
  const SmartFoodApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Food Donation',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.buildTheme(),
      home: const SplashPage(),
    );
  }
}
