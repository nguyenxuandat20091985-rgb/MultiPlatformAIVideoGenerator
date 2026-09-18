import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'services/api_service.dart';
import 'services/settings_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MultiPlatformVideoApp());
}

class MultiPlatformVideoApp extends StatefulWidget {
  const MultiPlatformVideoApp({super.key});

  @override
  State<MultiPlatformVideoApp> createState() => _MultiPlatformVideoAppState();
}

class _MultiPlatformVideoAppState extends State<MultiPlatformVideoApp> {
  ApiService? _api;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final url = await SettingsService.instance.getApiBaseUrl();
    if (!mounted) return;
    setState(() {
      _api = ApiService(baseUrl: url);
      _loading = false;
    });
  }

  void _onApiUrlChanged(String url) {
    _api?.setBaseUrl(url);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Video Generator',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF5B2EFF),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        inputDecorationTheme: const InputDecorationTheme(filled: true),
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF5B2EFF),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: _loading || _api == null
          ? const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            )
          : HomeScreen(
              api: _api!,
              onApiUrlChanged: _onApiUrlChanged,
            ),
    );
  }
}
