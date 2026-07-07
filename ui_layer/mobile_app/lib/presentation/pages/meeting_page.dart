import 'dart:math';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import '../../core/theme.dart';
import '../../data/services/meeting_service.dart';
import 'package:animate_do/animate_do.dart';

class MeetingPage extends StatefulWidget {
  final String roomId;
  final String roomName;

  const MeetingPage({
    super.key,
    required this.roomId,
    required this.roomName,
  });

  @override
  State<MeetingPage> createState() => _MeetingPageState();
}

class _MeetingPageState extends State<MeetingPage> {
  CameraController? _cameraController;
  late MeetingService _meetingService;
  bool _isInitializing = true;
  String? _lastTranslation;
  double _lastConfidence = 0.0;
  bool _showTranslation = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
    _meetingService = context.read<MeetingService>();
    _meetingService.connect();
    _meetingService.joinRoom(widget.roomId);
    
    _meetingService.translationStream.listen((data) {
      if (mounted) {
        setState(() {
          _lastTranslation = data['sign'];
          _lastConfidence = data['confidence'] ?? 0.0;
          _showTranslation = true;
        });
        // Hide overlay after 3 seconds
        Future.delayed(const Duration(seconds: 3), () {
          if (mounted) setState(() => _showTranslation = false);
        });
      }
    });
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return;

    // Use front camera by default
    final front = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );

    _cameraController = CameraController(
      front,
      ResolutionPreset.medium,
      enableAudio: false,
    );

    try {
      await _cameraController!.initialize();
      // Start image stream for landmark detection (simulated here)
      // In a real app, landmarks would be extracted and sent via _meetingService.sendLandmarks
    } catch (e) {
      debugPrint('Camera Error: $e');
    }

    if (mounted) setState(() => _isInitializing = false);
  }

  Future<void> _toggleCameraLens() async {
    final cameras = await availableCameras();
    if (cameras.length < 2) return;

    final currentLens = _cameraController!.description.lensDirection;
    final next = cameras.firstWhere(
      (c) => c.lensDirection != currentLens,
      orElse: () => cameras.first,
    );

    await _cameraController?.dispose();
    _cameraController = CameraController(next, ResolutionPreset.medium, enableAudio: false);
    await _cameraController!.initialize();
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final meeting = context.watch<MeetingService>();
    final size = MediaQuery.of(context).size;
    final isDesktop = size.width > 900;

    return Scaffold(
      backgroundColor: AppTheme.darkColor,
      body: SafeArea(
        child: Column(
          children: [
            _buildTopBar(),
            Expanded(
              child: Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: _buildVideoGrid(meeting),
                  ),
                  if (isDesktop) _buildSidePanel(meeting),
                ],
              ),
            ),
            _buildControlBar(meeting),
          ],
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.darkColor,
        border: Border(bottom: BorderSide(color: Colors.white.withOpacity(0.05))),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.emerald.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              children: [
                const Icon(Icons.circle, size: 8, color: Colors.emerald),
                const SizedBox(width: 8),
                Text(
                  'LIVE: ${widget.roomName}',
                  style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          const Spacer(),
          Text(
            'Room ID: ${widget.roomId}',
            style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 10, letterSpacing: 1),
          ),
          const SizedBox(width: 20),
          IconButton(
            icon: const Icon(Icons.flip_camera_ios, color: Colors.white54, size: 18),
            onPressed: _toggleCameraLens,
          ),
          const SizedBox(width: 20),
          Icon(Icons.people_outline, color: Colors.white.withOpacity(0.5), size: 16),
          const SizedBox(width: 6),
          Text(
            '${context.watch<MeetingService>().participants.length + 1}',
            style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildVideoGrid(MeetingService meeting) {
    final allParticipants = meeting.participants;
    final total = allParticipants.length + 1;
    
    int columns = (total <= 1) ? 1 : (total <= 4 ? 2 : 3);
    
    return Padding(
      padding: const EdgeInsets.all(12.0),
      child: Stack(
        children: [
          GridView.builder(
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: columns,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 16 / 9,
            ),
            itemCount: total,
            itemBuilder: (context, index) {
              if (index == 0) return _buildLocalPreview(meeting);
              return _buildRemoteParticipant(allParticipants[index - 1]);
            },
          ),
          if (_showTranslation)
            Align(
              alignment: Alignment.topCenter,
              child: FadeInDown(
                duration: const Duration(milliseconds: 300),
                child: Container(
                  margin: const EdgeInsets.only(top: 20),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryColor,
                    borderRadius: BorderRadius.circular(30),
                    boxShadow: [
                      BoxShadow(color: AppTheme.primaryColor.withOpacity(0.4), blurRadius: 20),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _lastTranslation ?? '',
                        style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.black),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 60,
                            height: 4,
                            decoration: BoxDecoration(
                              color: Colors.white24,
                              borderRadius: BorderRadius.circular(2),
                            ),
                            child: Align(
                              alignment: Alignment.centerLeft,
                              child: Container(
                                width: 60 * _lastConfidence,
                                decoration: BoxDecoration(
                                  color: Colors.white,
                                  borderRadius: BorderRadius.circular(2),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '${(_lastConfidence * 100).toInt()}%',
                            style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildLocalPreview(MeetingService meeting) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF262626),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppTheme.primaryColor.withOpacity(0.3), width: 2),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          if (_isInitializing)
            const Center(child: CircularProgressIndicator())
          else if (!meeting.isCameraOn)
            const Center(child: Icon(Icons.videocam_off, color: Colors.white24, size: 48))
          else
            // Mirroring the local camera preview as requested
            Transform.scale(
              scaleX: -1.0,
              child: SizedBox.expand(
                child: CameraPreview(_cameraController!),
              ),
            ),
          
          Positioned(
            bottom: 12,
            left: 12,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black45,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text('You (Interpreter)', style: TextStyle(color: Colors.white, fontSize: 10)),
            ),
          ),
          
          if (meeting.isHandRaised)
            const Positioned(
              top: 12,
              right: 12,
              child: CircleAvatar(
                backgroundColor: Colors.amber,
                radius: 12,
                child: Icon(Icons.pan_tool, size: 12, color: Colors.black),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildRemoteParticipant(MeetingParticipant p) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF262626),
        borderRadius: BorderRadius.circular(24),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // Placeholder for remote video (WebRTC stream would go here)
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircleAvatar(
                  radius: 30,
                  backgroundColor: AppTheme.primaryColor.withOpacity(0.1),
                  child: Text(p.username[0].toUpperCase(), style: const TextStyle(color: AppTheme.primaryColor, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(height: 12),
                Text(p.username, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          
          if (p.isMuted)
            const Positioned(
              top: 12,
              left: 12,
              child: Icon(Icons.mic_off, color: Colors.red, size: 16),
            ),

          Positioned(
            bottom: 12,
            left: 12,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black45,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(p.username, style: const TextStyle(color: Colors.white, fontSize: 10)),
            ),
          ),

          if (p.lastTranslation != null)
             Positioned(
              bottom: 40,
              left: 12,
              right: 12,
              child: FadeInUp(
                duration: const Duration(milliseconds: 200),
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.black87,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.primaryColor.withOpacity(0.5)),
                  ),
                  child: Text(
                    p.lastTranslation!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppTheme.primaryColor, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSidePanel(MeetingService meeting) {
    return Container(
      width: 300,
      color: const Color(0xFF1E1E1E),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text('Translation Feed', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: meeting.translationHistory.length,
              itemBuilder: (context, index) {
                final item = meeting.translationHistory[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(item['user'], style: const TextStyle(color: AppTheme.primaryColor, fontWeight: FontWeight.bold, fontSize: 10)),
                      const SizedBox(height: 4),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(item['text'], style: const TextStyle(color: Colors.white, fontSize: 13)),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildControlBar(MeetingService meeting) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 20),
      color: AppTheme.darkColor,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildControlBtn(
            icon: meeting.isMuted ? Icons.mic_off : Icons.mic,
            color: meeting.isMuted ? Colors.red : Colors.white12,
            onTap: () => meeting.toggleMute(),
          ),
          const SizedBox(width: 16),
          _buildControlBtn(
            icon: meeting.isCameraOn ? Icons.videocam : Icons.videocam_off,
            color: meeting.isCameraOn ? Colors.white12 : Colors.red,
            onTap: () => meeting.toggleCamera(),
          ),
          const SizedBox(width: 16),
          _buildControlBtn(
            icon: Icons.pan_tool,
            color: meeting.isHandRaised ? Colors.amber : Colors.white12,
            onTap: () => meeting.toggleHandRaise(),
          ),
          const SizedBox(width: 16),
          _buildControlBtn(
            icon: Icons.chat_bubble_outline,
            color: Colors.white12,
            onTap: () {},
          ),
          const SizedBox(width: 16),
          _buildControlBtn(
            icon: Icons.call_end,
            color: Colors.red,
            isRound: false,
            onTap: () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }

  Widget _buildControlBtn({required IconData icon, required Color color, required VoidCallback onTap, bool isRound = true}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(isRound ? 30 : 16),
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          color: color,
          shape: isRound ? BoxShape.circle : BoxShape.rectangle,
          borderRadius: isRound ? null : BorderRadius.circular(16),
        ),
        child: Icon(icon, color: Colors.white),
      ),
    );
  }
}
