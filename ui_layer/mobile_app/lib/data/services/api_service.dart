import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  final String? token;
  static const String baseUrl = 'http://localhost:8000'; // Change for production

  ApiService(this.token);

  Map<String, String> get _headers => {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  };

  Future<dynamic> getStats() async {
    final res = await http.get(Uri.parse('$baseUrl/admin/stats'), headers: _headers);
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Failed to load stats');
  }

  Future<List<dynamic>> getDatasets() async {
    final res = await http.get(Uri.parse('$baseUrl/admin/datasets'), headers: _headers);
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Failed to load datasets');
  }

  Future<List<dynamic>> getGestures() async {
    final res = await http.get(Uri.parse('$baseUrl/admin/gestures'), headers: _headers);
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Failed to load gestures');
  }

  Future<dynamic> startTraining(int epochs) async {
    final res = await http.post(
      Uri.parse('$baseUrl/admin/training/jobs'),
      headers: _headers,
      body: json.encode({
        'job_name': 'Mobile Build ${DateTime.now().toLocal()}',
        'epochs': epochs,
      }),
    );
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Failed to start training');
  }

  // --- Meeting APIs ---
  Future<Map<String, dynamic>> createRoom(String name) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/meeting/rooms'),
      headers: _headers,
      body: json.encode({'room_name': name}),
    );
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Failed to create room');
  }

  Future<Map<String, dynamic>> getRoomDetails(String roomId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/meeting/rooms/$roomId'),
      headers: _headers,
    );
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Room not found');
  }

  // --- User APIs ---
  Future<List<dynamic>> getHistory() async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/user/history'),
      headers: _headers,
    );
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Failed to load history');
  }

  Future<List<dynamic>> getLibrary() async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/user/library'),
      headers: _headers,
    );
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Failed to load library');
  }

  Future<Map<String, dynamic>> getMyProfile() async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/user/profile/me'),
      headers: _headers,
    );
    if (res.statusCode == 200) return json.decode(res.body);
    throw Exception('Failed to load profile');
  }
}
