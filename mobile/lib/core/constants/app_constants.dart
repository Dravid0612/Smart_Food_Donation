class AppConstants {
  static const String appName = 'Smart Food Donation';
  static const String appTagline = 'Turn Surplus Food Into Shared Meals';
  
  // API URL:
  //   Android Emulator → 10.0.2.2:8000
  //   Physical Device  → replace with your machine's LAN IP, e.g. 192.168.1.X:8000
  //   iOS Simulator    → 127.0.0.1:8000
  static const String apiBaseUrl = 'http://10.0.2.2:8000/api';
  
  // Storage Keys
  static const String keyAuthToken = 'auth_token';
  static const String keyUserData = 'user_data';
  static const String keyOnboardingComplete = 'onboarding_complete';
}
