import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class ApiConfig {
  // Use 10.0.2.2 if using Android Emulator, or your local IP if testing on a physical device.
  // For Windows/Web, localhost works.
  static const String baseUrl = "http://localhost:8000"; 

  // ---------------- INTERVIEW ENDPOINTS ----------------
  
  static Future<Map<String, dynamic>> evaluateInterview(String filePath) async {
    var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/evaluate_interview'));
    request.files.add(await http.MultipartFile.fromPath('audio', filePath));
    
    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);
    return json.decode(response.body);
  }

  // ---------------- GD MODULE ENDPOINTS ----------------

  /// Fetches a random GD topic from the MySQL database
  static Future<Map<String, dynamic>> fetchGDTopic() async {
    final response = await http.get(Uri.parse('$baseUrl/gd_module/gd/topic'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception("Failed to load GD topic");
    }
  }

  /// Submits the recorded .wav file to the GD evaluation pipeline
  static Future<Map<String, dynamic>> submitGDAudio({
    required int topicId, 
    required File audioFile
  }) async {
    var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/gd_module/gd/submit-audio'));
    
    request.fields['topic_id'] = topicId.toString();
    request.files.add(await http.MultipartFile.fromPath('audio', audioFile.path));
    
    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception("GD Evaluation failed");
    }
  }

  // ---------------- INDUSTRY NEWS ENDPOINTS ----------------

  static Future<List<dynamic>> fetchLatestNews() async {
    final response = await http.get(Uri.parse('$baseUrl/news/latest'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception("Failed to load industry news");
    }
  }
}