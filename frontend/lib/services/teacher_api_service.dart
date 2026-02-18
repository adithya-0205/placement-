import 'dart:convert';
import 'package:http/http.dart' as http;

class TeacherApiService {
  static const String baseUrl = 'http://127.0.0.1:8000';

  // Teacher Login
  static Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/teacher/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Login failed: ${response.body}');
    }
  }

  // Get All Students
  static Future<Map<String, dynamic>> getStudents({String? branch}) async {
    String url = '$baseUrl/teacher/students';
    if (branch != null && branch.isNotEmpty) {
      url += '?branch=$branch';
    }

    final response = await http.get(Uri.parse(url));

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load students');
    }
  }

  // Get Student Progress
  static Future<Map<String, dynamic>> getStudentProgress(String username) async {
    final response = await http.get(
      Uri.parse('$baseUrl/teacher/students/$username/progress'),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load student progress');
    }
  }

  // Get Dashboard Overview
  static Future<Map<String, dynamic>> getDashboardOverview() async {
    final response = await http.get(
      Uri.parse('$baseUrl/teacher/dashboard/overview'),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load dashboard overview');
    }
  }

  // Get Branch Analytics
  static Future<Map<String, dynamic>> getBranchAnalytics(String branch) async {
    final response = await http.get(
      Uri.parse('$baseUrl/teacher/dashboard/branch/$branch'),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load branch analytics');
    }
  }

  // Get Daily Activity
  static Future<Map<String, dynamic>> getDailyActivity({String? date}) async {
    String url = '$baseUrl/teacher/dashboard/activity';
    if (date != null && date.isNotEmpty) {
      url += '?date_str=$date';
    }

    final response = await http.get(Uri.parse(url));

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load daily activity');
    }
  }

  // Get Batch Trends (New)
  static Future<Map<String, dynamic>> getBatchTrends() async {
    final response = await http.get(
      Uri.parse('$baseUrl/teacher/dashboard/batch_trends'),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load batch trends');
    }
  }

  // Get AI Recommendations (New)
  static Future<Map<String, dynamic>> getAiRecommendations() async {
    final response = await http.get(
      Uri.parse('$baseUrl/teacher/dashboard/ai_recommendations'),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load AI recommendations');
    }
  }
}
