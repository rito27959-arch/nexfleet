import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;

/// Configuration de l'application NexFleet Mobile.
///
/// L'URL de l'API peut être forcée à la compilation :
/// `flutter run --dart-define=API_URL=https://parc.mondomaine.com`
class AppConfig {
  AppConfig._();

  static const String _envApi = String.fromEnvironment('API_URL');

  static String get baseUrl {
    if (_envApi.isNotEmpty) return _envApi;
    if (!kIsWeb && Platform.isAndroid) return 'http://10.0.2.2:5000';
    return 'http://127.0.0.1:5000';
  }

  static String get apiUrl => '$baseUrl/api';
}