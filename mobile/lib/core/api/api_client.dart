import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../constants/app_constants.dart';
import '../storage/secure_storage.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late Dio dio;
  final SecureStorageService _storage = SecureStorageService();
  VoidCallback? onSessionExpired;

  ApiClient._internal() {
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
        onError: (DioException error, handler) async {
          final isAuthEndpoint = error.requestOptions.path.contains('/auth/login') ||
              error.requestOptions.path.contains('/auth/refresh') ||
              error.requestOptions.path.contains('/auth/register');

          // Silent token refresh on 401 for non-auth requests
          if (error.response?.statusCode == 401 && !isAuthEndpoint) {
            final refreshToken = await _storage.getRefreshToken();
            if (refreshToken != null && refreshToken.isNotEmpty) {
              try {
                final refreshDio = Dio(BaseOptions(baseUrl: AppConstants.apiBaseUrl));
                final refreshResponse = await refreshDio.post(
                  '/auth/refresh',
                  data: {'refresh_token': refreshToken},
                  options: Options(headers: {'Content-Type': 'application/json'}),
                );

                if (refreshResponse.statusCode == 200 && refreshResponse.data != null) {
                  final newAccessToken = refreshResponse.data['access_token'];
                  final newRefreshToken = refreshResponse.data['refresh_token'];

                  await _storage.saveToken(newAccessToken);
                  if (newRefreshToken != null) {
                    await _storage.saveRefreshToken(newRefreshToken);
                  }

                  // Retry the original request with new token
                  final retryOptions = error.requestOptions;
                  retryOptions.headers['Authorization'] = 'Bearer $newAccessToken';
                  final retryResponse = await dio.fetch(retryOptions);
                  return handler.resolve(retryResponse);
                }
              } catch (_) {
                // Refresh failed or revoked — fall through to session expired
              }
            }

            // If refresh not possible or failed, trigger session expiry
            await _storage.clearAll();
            if (onSessionExpired != null) {
              onSessionExpired!();
            }
          }

          String userFriendlyMessage = 'We were unable to complete your request. Please try again.';
          if (error.type == DioExceptionType.connectionTimeout ||
              error.type == DioExceptionType.receiveTimeout) {
            userFriendlyMessage = 'The request took too long. Check your connection and try again.';
          } else if (error.type == DioExceptionType.connectionError) {
            userFriendlyMessage = 'We\'re having trouble connecting. Check your internet connection and try again.';
          } else if (error.response != null) {
            final statusCode = error.response?.statusCode;
            final data = error.response?.data;
            if (data is Map && data.containsKey('detail') && data['detail'] is String) {
              final detail = data['detail'].toString();
              // Filter out raw stack traces or internal python errors if any
              if (!detail.contains('Traceback') && !detail.contains('OperationalError') && !detail.contains('Internal Server')) {
                userFriendlyMessage = detail;
              } else {
                userFriendlyMessage = 'We couldn\'t complete that request right now. Please try again.';
              }
            } else if (statusCode == 401) {
              userFriendlyMessage = 'Your session has expired. Please log in again.';
            } else if (statusCode == 403) {
              userFriendlyMessage = 'You do not have permission to perform this rescue action.';
            } else if (statusCode == 404) {
              userFriendlyMessage = 'The requested rescue item could not be found.';
            } else if (statusCode == 409) {
              userFriendlyMessage = 'This donation has already been accepted or updated by another partner.';
            } else if (statusCode == 422) {
              userFriendlyMessage = 'Please check all required fields before continuing.';
            } else if (statusCode == 429) {
              userFriendlyMessage = 'Please wait a few seconds before requesting again.';
            } else if (statusCode != null && statusCode >= 500) {
              userFriendlyMessage = 'We couldn\'t complete that request right now. Please try again.';
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
