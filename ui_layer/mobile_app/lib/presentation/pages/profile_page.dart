import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../data/services/api_service.dart';
import '../../core/theme.dart';

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder<Map<String, dynamic>>(
        future: context.read<ApiService>().getMyProfile(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Error: ${snapshot.error}'));
          }
          final user = snapshot.data!;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Stack(
                  children: [
                    CircleAvatar(
                      radius: 60,
                      backgroundColor: Colors.grey[200],
                      backgroundImage: user['avatar_url'] != null ? NetworkImage(user['avatar_url']) : null,
                      child: user['avatar_url'] == null ? const Icon(Icons.person, size: 60, color: Colors.grey) : null,
                    ),
                    Positioned(
                      bottom: 0,
                      right: 0,
                      child: CircleAvatar(
                        backgroundColor: AppTheme.primaryColor,
                        radius: 18,
                        child: IconButton(
                          icon: const Icon(Icons.edit, size: 16, color: Colors.white),
                          onPressed: () {},
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Text(
                  user['name'] ?? user['username'],
                  style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                Text(
                  user['email'],
                  style: TextStyle(color: Colors.grey[500]),
                ),
                const SizedBox(height: 32),
                _buildInfoCard(
                  title: 'Bio',
                  content: user['bio'] ?? 'No bio set.',
                  icon: Icons.info_outline,
                ),
                const SizedBox(height: 16),
                _buildInfoCard(
                  title: 'Role',
                  content: user['role'].toString().toUpperCase(),
                  icon: Icons.verified_user_outlined,
                ),
                const SizedBox(height: 32),
                ElevatedButton(
                  onPressed: () {},
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size(double.infinity, 56),
                    backgroundColor: Colors.white,
                    foregroundColor: Colors.red,
                    side: const BorderSide(color: Colors.red),
                  ),
                  child: const Text('Delete Account'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildInfoCard({required String title, required String content, required IconData icon}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.grey[100]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: Colors.grey),
              const SizedBox(width: 8),
              Text(
                title.toUpperCase(),
                style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.grey),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(content, style: const TextStyle(fontSize: 16)),
        ],
      ),
    );
  }
}
