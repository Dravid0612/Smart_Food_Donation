class AppConstants {
  static const String appName = 'Smart Food Donation';
  static const String appTagline = 'Turn Surplus Food Into Shared Meals';
  
  // API URL: Default to localhost (10.0.2.2 for Android Emulator, 127.0.0.1 for local/desktop test)
  static const String apiBaseUrl = 'http://127.0.0.1:8000/api';
  
  // Storage Keys
  static const String keyAuthToken = 'auth_token';
  static const String keyUserData = 'user_data';
  static const String keyOnboardingComplete = 'onboarding_complete';
}
