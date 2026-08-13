import 'package:dio/dio.dart';
import '../constants/app_constants.dart';
import '../storage/secure_storage.dart';

class ApiClient {
  late Dio dio;
  final SecureStorageService _storage = SecureStorageService();

  ApiClient() {
    dio = Dio(
      BaseOptions(
        baseUrl: AppConstants.apiBaseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.getToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException error, handler) {
          String userFriendlyMessage = 'An unexpected network error occurred.';
          if (error.type == DioExceptionType.connectionTimeout ||
              error.type == DioExceptionType.receiveTimeout) {
            userFriendlyMessage = 'Connection timed out. Please check your internet connection.';
          } else if (error.type == DioExceptionType.connectionError) {
            userFriendlyMessage = 'Unable to connect to server. Ensure server is running.';
          } else if (error.response != null) {
            final data = error.response?.data;
            if (data is Map && data.containsKey('detail')) {
              userFriendlyMessage = data['detail'].toString();
            } else if (error.response?.statusCode == 401) {
              userFriendlyMessage = 'Session expired. Please log in again.';
            }
          }
          return handler.next(
            DioException(
              requestOptions: error.requestOptions,
              response: error.response,
              type: error.type,
              error: userFriendlyMessage,
            ),
          );
        },
      ),
    );
  }
}
