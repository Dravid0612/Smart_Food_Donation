/// OTP Service — Smart Food Rescue
/// Handles pickup OTP fetch, delivery status, regeneration, and volunteer verification.
///
/// SECURITY:
/// - Never stores plaintext OTP beyond displaying it in the authenticated screen.
/// - All calls use ApiClient with JWT Bearer token authentication.
/// - Volunteers cannot call getPickupOtpStatus() — the backend returns 403.
library otp_service;

import 'package:dio/dio.dart';
import '../core/api/api_client.dart';
import '../models/otp_delivery_model.dart';

class OtpService {
  final ApiClient _apiClient;

  OtpService([ApiClient? apiClient]) : _apiClient = apiClient ?? ApiClient();

  /// Fetches pickup OTP status for the authenticated donor.
  /// Returns [OtpDeliveryInfo] with delivery status and expiry info.
  Future<OtpDeliveryInfo> getPickupOtpStatus(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/pickup-otp');
      if (response.statusCode == 200 && response.data != null) {
        return OtpDeliveryInfo.fromJson(response.data as Map<String, dynamic>);
      }
      throw Exception('Failed to load pickup OTP status.');
    } on DioException catch (e) {
      if (e.response?.statusCode == 403) {
        throw Exception('Access denied. Only donors may view the pickup code.');
      }
      throw Exception('Failed to load pickup OTP: ${e.message}');
    }
  }

  /// Fetches the SMS delivery status for the pickup OTP.
  /// Use this for the ✅/⚠/❌ status indicator in donor dashboard.
  Future<OtpDeliveryInfo> getOtpDeliveryStatus(int donationId) async {
    try {
      final response = await _apiClient.dio.get('/donations/$donationId/otp-delivery-status');
      if (response.statusCode == 200 && response.data != null) {
        return OtpDeliveryInfo.fromJson(response.data as Map<String, dynamic>);
      }
      throw Exception('Failed to load OTP delivery status.');
    } on DioException catch (e) {
      throw Exception('Failed to load OTP delivery status: ${e.message}');
    }
  }

  /// Generates a new pickup OTP and sends SMS to donor's verified phone.
  /// Returns [PickupOtpGenerateResult] with plaintext OTP — show immediately, do not store.
  /// Rate-limited: max 3 per 10 minutes.
  Future<PickupOtpGenerateResult> regeneratePickupOtp(int donationId) async {
    try {
      final response = await _apiClient.dio.post('/donations/$donationId/pickup-otp/regenerate');
      if (response.statusCode == 200 && response.data != null) {
        return PickupOtpGenerateResult.fromJson(response.data as Map<String, dynamic>);
      }
      throw Exception('Failed to regenerate OTP.');
    } on DioException catch (e) {
      if (e.response?.statusCode == 429) {
        final data = e.response?.data;
        final msg = data is Map ? (data['detail'] as String? ?? 'Please wait before requesting another code.') : 'Rate limited.';
        throw RateLimitException(msg);
      }
      throw Exception('Failed to regenerate OTP: ${e.message}');
    }
  }

  /// Volunteer verifies the OTP shown by the donor.
  /// On success: donation transitions to "collected".
  Future<bool> verifyPickupOtp(int donationId, String otp) async {
    try {
      final response = await _apiClient.dio.post(
        '/donations/$donationId/pickup-otp/verify',
        data: {'otp': otp},
      );
      return response.statusCode == 200;
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      if (code == 400) {
        throw IncorrectOtpException('Incorrect code. Please ask the donor to show the code again.');
      } else if (code == 409) {
        throw ReplayOtpException('This code has already been used. Ask the donor for a new code.');
      } else if (code == 410) {
        throw ExpiredOtpException('This code has expired. Ask the donor to generate a new code.');
      } else if (code == 403) {
        throw Exception('You are not assigned to this donation.');
      }
      throw Exception('OTP verification failed: ${e.message}');
    }
  }
}

/// Custom exceptions for user-friendly error handling in UI

class RateLimitException implements Exception {
  final String message;
  RateLimitException(this.message);
  @override
  String toString() => message;
}

class IncorrectOtpException implements Exception {
  final String message;
  IncorrectOtpException(this.message);
  @override
  String toString() => message;
}

class ReplayOtpException implements Exception {
  final String message;
  ReplayOtpException(this.message);
  @override
  String toString() => message;
}

class ExpiredOtpException implements Exception {
  final String message;
  ExpiredOtpException(this.message);
  @override
  String toString() => message;
}
