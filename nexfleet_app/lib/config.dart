import 'package:flutter/foundation.dart' show kIsWeb;

/// Configuration de l'application NexFleet Mobile.
///
/// L'URL de l'API peut être forcée à la compilation :
/// `flutter run --dart-define=API_URL=http://127.0.0.1:5000`
class AppConfig {
  AppConfig._();

  static const String _envApi = String.fromEnvironment('API_URL');

  /// Serveur par défaut : IP du PC sur le réseau du téléphone (hotspot).
  /// Docs : IP du PC via `hostname -I`. En ligne : URL Render/tunnel.
  static const String _defaultApi = 'http://172.20.10.6:5000';

  static String get baseUrl {
    if (_envApi.isNotEmpty) return _envApi;
    return _defaultApi;
  }

  static String get apiUrl => '$baseUrl/api';
}