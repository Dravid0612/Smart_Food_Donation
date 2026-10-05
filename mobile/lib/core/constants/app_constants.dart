import 'package:flutter/foundation.dart';

enum Environment { development, staging, production }

class AppConstants {
  static const String appName = 'Smart Food Donation';
  static const String appTagline = 'Every plate, matched to a need.';
  
  // Environment resolution via --dart-define=ENVIRONMENT=production / staging / development
  static const String _envName = String.fromEnvironment('ENVIRONMENT', defaultValue: kReleaseMode ? 'production' : 'development');

  static Environment get environment {
    switch (_envName.toLowerCase()) {
      case 'production':
      case 'prod':
        return Environment.production;
      case 'staging':
      case 'demo':
        return Environment.staging;
      case 'development':
      case 'dev':
      default:
        return kReleaseMode ? Environment.production : Environment.development;
    }
  }

  // API URL resolution:
  // Can be overridden at build time via:
  //   flutter build apk --dart-define=API_BASE_URL=https://smart-food-donation-h1dz.onrender.com/api
  static const String _customApiUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');

  static String get apiBaseUrl {
    if (_customApiUrl.isNotEmpty) {
      return _customApiUrl;
    }
    switch (environment) {
      case Environment.production:
        return 'https://smart-food-donation-h1dz.onrender.com/api';
      case Environment.staging:
        return 'https://smart-food-donation-h1dz.onrender.com/api';
      case Environment.development:
        return 'http://10.0.2.2:8000/api';
    }
  }
  
  // Storage Keys
  static const String keyAuthToken = 'auth_token';
  static const String keyRefreshToken = 'refresh_token';
  static const String keyUserData = 'user_data';
  static const String keyOnboardingComplete = 'onboarding_complete';
  static const String keyFcmToken = 'fcm_device_token';
}
