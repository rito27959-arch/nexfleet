import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import 'session.dart';

class ApiException implements Exception {
  final String message;
  final int? status;

  ApiException(this.message, [this.status]);

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient(this.session);

  final Session session;

  Uri _uri(String path, [Map<String, String>? query]) =>
      Uri.parse('${AppConfig.baseUrl}$path').replace(queryParameters: query);

  Map<String, String> _headers({bool json = true}) {
    final h = <String, String>{'Accept': 'application/json'};
    final t = session.token;
    if (t != null && t.isNotEmpty) h['Authorization'] = 'Bearer $t';
    if (json) h['Content-Type'] = 'application/json';
    return h;
  }

  Future<Map<String, dynamic>> _handle(http.Response r) async {
    dynamic body;
    try {
      body = jsonDecode(utf8.decode(r.bodyBytes));
    } catch (_) {
      body = null;
    }
    if (r.statusCode >= 200 && r.statusCode < 300) {
      if (body is Map<String, dynamic>) return body;
      return <String, dynamic>{};
    }
    final msg = body is Map<String, dynamic> && body['error'] is String
        ? body['error'] as String
        : 'Erreur serveur (${r.statusCode}).';
    throw ApiException(msg, r.statusCode);
  }

  Future<Map<String, dynamic>> get(String path,
      [Map<String, String>? query]) async {
    final r = await http
        .get(_uri(path, query), headers: _headers())
        .timeout(const Duration(seconds: 15));
    return _handle(r);
  }

  Future<Map<String, dynamic>> post(String path,
      [Map<String, dynamic>? body]) async {
    final r = await http
        .post(_uri(path),
            headers: _headers(), body: jsonEncode(body ?? const {}))
        .timeout(const Duration(seconds: 15));
    return _handle(r);
  }

  Future<Map<String, dynamic>> put(String path,
      [Map<String, dynamic>? body]) async {
    final r = await http
        .put(_uri(path),
            headers: _headers(), body: jsonEncode(body ?? const {}))
        .timeout(const Duration(seconds: 15));
    return _handle(r);
  }

  Future<Map<String, dynamic>> delete(String path) async {
    final r = await http
        .delete(_uri(path), headers: _headers())
        .timeout(const Duration(seconds: 15));
    return _handle(r);
  }
}