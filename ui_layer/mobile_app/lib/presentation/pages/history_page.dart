import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../../data/services/api_service.dart';
import '../../core/theme.dart';

class HistoryPage extends StatelessWidget {
  const HistoryPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder<List<dynamic>>(
        future: context.read<ApiService>().getHistory(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Error: ${snapshot.error}'));
          }
          final items = snapshot.data ?? [];
          if (items.isEmpty) {
            return const Center(child: Text('No translation history found.'));
          }

          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            separatorBuilder: (context, index) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final item = items[index];
              final date = DateTime.parse(item['timestamp']);
              final timeStr = DateFormat('MMM d, h:mm a').format(date);
              final isSign = item['message_type'] == 'sign';

              return Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.grey[200]!),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: (isSign ? AppTheme.primaryColor : Colors.blue).withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        isSign ? Icons.back_hand : Icons.mic,
                        color: isSign ? AppTheme.primaryColor : Colors.blue,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                item['message_type'].toString().toUpperCase(),
                                style: TextStyle(
                                  color: isSign ? AppTheme.primaryColor : Colors.blue,
                                  fontSize: 10,
                                  fontWeight: FontWeight.black,
                                ),
                              ),
                              Text(
                                timeStr,
                                style: TextStyle(color: Colors.grey[400], fontSize: 10),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            item['original_content'] ?? '',
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                          Text(
                            item['translated_content'] ?? '',
                            style: TextStyle(color: Colors.grey[600], fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 16),
                    Column(
                      children: [
                        const Text('CONF', style: TextStyle(fontSize: 8, fontWeight: FontWeight.bold, color: Colors.grey)),
                        Text(
                          '${((item['confidence'] ?? 0.0) * 100).toStringAsFixed(1)}%',
                          style: const TextStyle(fontWeight: FontWeight.black, color: Colors.emerald, fontSize: 12),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}
