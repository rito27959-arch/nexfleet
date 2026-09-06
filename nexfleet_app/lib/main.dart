import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'core/app_scope.dart';
import 'core/theme.dart';
import 'screens/splash_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
      systemNavigationBarColor: Color(0xFF05070F),
    ),
  );
  runApp(const NexFleetApp());
}

class NexFleetApp extends StatelessWidget {
  const NexFleetApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder(
      valueListenable: app.session.loggedIn,
      builder: (context, _, __) => MaterialApp(
        title: 'NexFleet',
        debugShowCheckedModeBanner: false,
        theme: buildTheme(),
        home: const SplashScreen(),
      ),
    );
  }
}