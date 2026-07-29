import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String _baseUrl = 'http://10.0.2.2:8000';

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );

    return _decode(response);
  }

  Future<Map<String, dynamic>> register(String name, String email, String password, String role) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'name': name, 'email': email, 'password': password, 'role': role}),
    );

    return _decode(response);
  }

  Future<List<dynamic>> fetchDonations(String token) async {
    final response = await http.get(
      Uri.parse('$_baseUrl/donations'),
      headers: {'Authorization': 'Bearer $token'},
    );
    final decoded = _decode(response);
    return decoded['data'] as List<dynamic>? ?? [];
  }

  Future<List<dynamic>> fetchAvailableDonations(String token) async {
    final response = await http.get(
      Uri.parse('$_baseUrl/donations/available'),
      headers: {'Authorization': 'Bearer $token'},
    );
    final decoded = _decode(response);
    return decoded['data'] as List<dynamic>? ?? [];
  }

  Future<Map<String, dynamic>> updateDonationStatus(String token, int id, String status) async {
    final response = await http.patch(
      Uri.parse('$_baseUrl/donations/$id/status'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({'status': status}),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> createDonation(String token, Map<String, dynamic> donation) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/donations'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(donation),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> updateDonation(String token, String id, Map<String, dynamic> donation) async {
    final response = await http.put(
      Uri.parse('$_baseUrl/donations/$id'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(donation),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> deleteDonation(String token, String id) async {
    final response = await http.delete(
      Uri.parse('$_baseUrl/donations/$id'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> fetchDashboard(String token) async {
    final response = await http.get(
      Uri.parse('$_baseUrl/admin/dashboard'),
      headers: {'Authorization': 'Bearer $token'},
    );
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    if (response.body.isEmpty) {
      return {'success': response.statusCode < 400};
    }

    final decoded = jsonDecode(response.body);
    if (response.statusCode >= 400) {
      final message = decoded is Map<String, dynamic> ? decoded['detail']?.toString() : null;
      throw ApiException(message ?? 'Request failed (${response.statusCode})');
    }
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    return {'data': decoded};
  }
}

class ApiException implements Exception {
  ApiException(this.message);
  final String message;

  @override
  String toString() => message;
}
