import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class MeetingParticipant {
  final String userId;
  final String username;
  bool isMuted;
  bool isCameraOn;
  bool isHandRaised;
  String? lastTranslation;

  MeetingParticipant({
    required this.userId,
    required this.username,
    this.isMuted = false,
    this.isCameraOn = true,
    this.isHandRaised = false,
    this.lastTranslation,
  });

  factory MeetingParticipant.fromJson(Map<String, dynamic> json) {
    return MeetingParticipant(
      userId: json['user_id'].toString(),
      username: json['username'] ?? 'Unknown',
      isMuted: json['is_muted'] ?? false,
      isCameraOn: json['camera_on'] ?? true,
      isHandRaised: json['hand_raised'] ?? false,
    );
  }
}

class MeetingService extends ChangeNotifier {
  WebSocketChannel? _channel;
  final String? token;
  final String baseUrl = 'ws://localhost:8000/ws/translate';

  List<MeetingParticipant> participants = [];
  String? currentRoomId;
  bool isConnected = false;
  
  List<Map<String, dynamic>> translationHistory = [];

  // Local state
  bool isMuted = false;
  bool isCameraOn = true;
  bool isHandRaised = false;

  final _translationController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get translationStream => _translationController.stream;

  MeetingService(this.token);

  void connect() {
    if (token == null) return;
    
    final uri = Uri.parse('$baseUrl?token=$token');
    _channel = WebSocketChannel.connect(uri);
    isConnected = true;
    notifyListeners();

    _channel!.stream.listen(
      (message) {
        final data = json.decode(message);
        _handleMessage(data);
      },
      onDone: () {
        isConnected = false;
        notifyListeners();
      },
      onError: (error) {
        debugPrint('WebSocket Error: $error');
        isConnected = false;
        notifyListeners();
      },
    );
  }

  void _handleMessage(Map<String, dynamic> data) {
    final type = data['type'];

    switch (type) {
      case 'room_state':
        currentRoomId = data['room_id'];
        final List<dynamic> parts = data['participants'];
        participants = parts.map((p) => MeetingParticipant.fromJson(p)).toList();
        notifyListeners();
        break;

      case 'participant_joined':
        final p = MeetingParticipant.fromJson(data['info']);
        participants.removeWhere((existing) => existing.userId == p.userId);
        participants.add(p);
        notifyListeners();
        break;

      case 'participant_left':
        participants.removeWhere((p) => p.userId == data['user_id'].toString());
        notifyListeners();
        break;

      case 'meeting_action':
        final userId = data['user_id'].toString();
        final action = data['action'];
        final value = data['value'];
        
        final idx = participants.indexWhere((p) => p.userId == userId);
        if (idx != -1) {
          if (action == 'mute') participants[idx].isMuted = value;
          if (action == 'camera') participants[idx].isCameraOn = value;
          if (action == 'hand_raise') participants[idx].isHandRaised = value;
          notifyListeners();
        }
        break;

      case 'prediction':
        _translationController.add(data);
        translationHistory.insert(0, {
          'user': 'You',
          'text': data['sign'],
          'time': DateTime.now(),
        });
        notifyListeners();
        break;

      case 'remote_translation':
        final userId = data['user_id'].toString();
        final idx = participants.indexWhere((p) => p.userId == userId);
        if (idx != -1) {
          participants[idx].lastTranslation = data['sign'];
          translationHistory.insert(0, {
            'user': participants[idx].username,
            'text': data['sign'],
            'time': DateTime.now(),
          });
          notifyListeners();
          // Clear translation after 3 seconds
          Future.delayed(const Duration(seconds: 3), () {
            if (idx < participants.length && participants[idx].userId == userId) {
              participants[idx].lastTranslation = null;
              notifyListeners();
            }
          });
        }
        break;
      
      case 'webrtc_offer':
      case 'webrtc_answer':
      case 'webrtc_ice_candidate':
        // These would be handled by a WebRTC manager
        debugPrint('Signaling received: $type from ${data['sender_id']}');
        break;
    }
  }

  void joinRoom(String roomId) {
    if (_channel == null) return;
    _channel!.sink.add(json.encode({
      'type': 'join_room',
      'room_id': roomId,
    }));
  }

  void toggleMute() {
    isMuted = !isMuted;
    _sendAction('mute', isMuted);
    notifyListeners();
  }

  void toggleCamera() {
    isCameraOn = !isCameraOn;
    _sendAction('camera', isCameraOn);
    notifyListeners();
  }

  void toggleHandRaise() {
    isHandRaised = !isHandRaised;
    _sendAction('hand_raise', isHandRaised);
    notifyListeners();
  }

  void _sendAction(String action, dynamic value) {
    if (_channel == null) return;
    _channel!.sink.add(json.encode({
      'type': 'meeting_action',
      'action': action,
      'value': value,
    }));
  }

  void sendLandmarks(List<double> landmarks) {
    if (_channel == null) return;
    // Sending as bytes as expected by the backend for efficiency
    _channel!.sink.add(Float32List.fromList(landmarks).buffer.asUint8List());
  }

  @override
  void dispose() {
    _channel?.sink.close();
    _translationController.close();
    super.dispose();
  }
}
