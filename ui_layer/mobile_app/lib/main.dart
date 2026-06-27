import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'core/theme.dart';
import 'data/services/api_service.dart';
import 'data/services/auth_service.dart';
import 'presentation/pages/login_page.dart';
import 'presentation/pages/home_page.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthService()),
        ProxyProvider<AuthService, ApiService>(
          update: (_, auth, __) => ApiService(auth.token),
        ),
      ],
      child: const SnLagApp(),
    ),
  );
}

class SnLagApp extends StatelessWidget {
  const SnLagApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SnLag HQ',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: Consumer<AuthService>(
        builder: (context, auth, _) {
          return auth.isAuthenticated ? const HomePage() : const LoginPage();
        },
      ),
    );
  }
}
