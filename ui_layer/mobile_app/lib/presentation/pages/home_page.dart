import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../data/services/auth_service.dart';
import '../../core/theme.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;

  final List<Widget> _pages = [
    const Center(child: Text('Command Hub')),
    const Center(child: Text('Neural Forge')),
    const Center(child: Text('Semantic Library')),
    const Center(child: Text('Deep Training')),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SnLag CORE', style: TextStyle(fontWeight: FontWeight.w900)),
        actions: [
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
          BottomNavigationBarItem(icon: Icon(Icons.memory), label: 'Forge'),
          BottomNavigationBarItem(icon: Icon(Icons.translate), label: 'Library'),
          BottomNavigationBarItem(icon: Icon(Icons.psychology), label: 'Training'),
        ],
      ),
    );
  }
}
