import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../data/services/auth_service.dart';
import '../../data/services/api_service.dart';
import '../../core/theme.dart';
import 'meeting_page.dart';
import 'library_page.dart';
import 'history_page.dart';
import 'profile_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      const DashboardHub(),
      const VisionHub(),
      const LibraryPage(),
      const ProfilePage(),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SnLag CORE', style: TextStyle(fontWeight: FontWeight.w900)),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const HistoryPage())),
          ),
          IconButton(
            icon: const Icon(Icons.power_settings_new),
            onPressed: () => context.read<AuthService>().logout(),
          ),
        ],
      ),
      body: _pages[_selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (index) => setState(() => _selectedIndex = index),
        type: BottomNavigationBarType.fixed,
        selectedItemColor: AppTheme.primaryColor,
        unselectedItemColor: Colors.grey,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dashboard), label: 'Hub'),
          BottomNavigationBarItem(icon: Icon(Icons.videocam), label: 'Vision'),
          BottomNavigationBarItem(icon: Icon(Icons.book), label: 'Library'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}

class DashboardHub extends StatelessWidget {
  const DashboardHub({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Personal Neural Hub',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Your progress across the neural ecosystem.',
            style: TextStyle(color: Colors.grey),
          ),
          const SizedBox(height: 32),
          _buildStats(context),
          const SizedBox(height: 32),
          const Text('Quick Actions', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          _buildActionCard(
            context,
            title: 'Neural Vision',
            subtitle: 'Start real-time translation session.',
            icon: Icons.camera_enhance,
            color: AppTheme.primaryColor,
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const VisionHub())),
          ),
          const SizedBox(height: 16),
          _buildActionCard(
            context,
            title: 'Explore Library',
            subtitle: 'Browse 100+ sign language gestures.',
            icon: Icons.menu_book,
            color: Colors.blue,
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const LibraryPage())),
          ),
        ],
      ),
    );
  }

  Widget _buildStats(BuildContext context) {
    return FutureBuilder(
      future: Future.wait([
        context.read<ApiService>().getHistory(),
        context.read<ApiService>().getLibrary(),
      ]),
      builder: (context, snapshot) {
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        final history = snapshot.data![0] as List;
        final library = snapshot.data![1] as List;
        final signsLearned = history.where((h) => h['message_type'] == 'sign').length;

        return GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 16,
          crossAxisSpacing: 16,
          childAspectRatio: 1.5,
          children: [
            _buildStatCard('Signs Detected', signsLearned.toString(), Icons.handshake, Colors.orange),
            _buildStatCard('Library Size', library.length.toString(), Icons.library_books, Colors.blue),
            _buildStatCard('Total Sessions', history.length.toString(), Icons.history, Colors.purple),
            _buildStatCard('Active Hubs', '1', Icons.hub, Colors.emerald),
          ],
        );
      },
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 16),
          const Spacer(),
          Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          Text(label, style: const TextStyle(fontSize: 10, color: Colors.grey, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}

class VisionHub extends StatelessWidget {
  const VisionHub({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Live Vision & Meetings',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Start a professional translation session or join a collaborative meeting.',
            style: TextStyle(color: Colors.grey),
          ),
          const SizedBox(height: 32),
          _buildActionCard(
            context,
            title: 'Host a New Meeting',
            subtitle: 'Start a room and invite participants for real-time translation.',
            icon: Icons.add_to_queue,
            color: AppTheme.primaryColor,
            onTap: () => _handleCreateRoom(context),
          ),
          const SizedBox(height: 16),
          _buildActionCard(
            context,
            title: 'Join with Room Code',
            subtitle: 'Enter an 8-character code to join an existing session.',
            icon: Icons.group_add,
            color: Colors.blue,
            onTap: () => _handleJoinRoom(context),
          ),
        ],
      ),
    );
  }

  Widget _buildActionCard(BuildContext context, {required String title, required String subtitle, required IconData icon, required Color color, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: color.withOpacity(0.05),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color.withOpacity(0.1)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 4),
                  Text(subtitle, style: TextStyle(color: Colors.grey[600], fontSize: 12)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleCreateRoom(BuildContext context) async {
    final api = context.read<ApiService>();
    try {
      final room = await api.createRoom('Discussion Room');
      if (context.mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => MeetingPage(
              roomId: room['room_id'],
              roomName: room['room_name'],
            ),
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  Future<void> _handleJoinRoom(BuildContext context) async {
    final controller = TextEditingController();
    final roomId = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Join Meeting'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(hintText: 'Enter Room Code (e.g. AB12CD34)'),
          textCapitalization: TextCapitalization.characters,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(context, controller.text.trim().toUpperCase()), child: const Text('Join')),
        ],
      ),
    );

    if (roomId != null && roomId.isNotEmpty && context.mounted) {
      final api = context.read<ApiService>();
      try {
        final room = await api.getRoomDetails(roomId);
        if (context.mounted) {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => MeetingPage(
                roomId: room['room_id'],
                roomName: room['room_name'],
              ),
            ),
          );
        }
      } catch (e) {
        if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Room not found')));
      }
    }
  }
}
