import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Session : jeton JWT + profil utilisateur, persistés localement.
class Session {
  static const _kToken = 'nx_token';
  static const _kUser = 'nx_user';

  final ValueNotifier<bool> loggedIn = ValueNotifier(false);

  String? token;
  Map<String, dynamic>? user;

  String? get username => user?['username'] as String?;
  String? get role => user?['role'] as String?;
  bool get isAdmin => role == 'admin';

  Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    token = p.getString(_kToken);
    final u = p.getString(_kUser);
    user = u != null ? jsonDecode(u) as Map<String, dynamic> : null;
    loggedIn.value = token != null && token!.isNotEmpty;
  }

  Future<void> save(String tk, Map<String, dynamic> usr) async {
    token = tk;
    user = usr;
    final p = await SharedPreferences.getInstance();
    await p.setString(_kToken, tk);
    await p.setString(_kUser, jsonEncode(usr));
    loggedIn.value = true;
  }

  Future<void> clear() async {
    token = null;
    user = null;
    final p = await SharedPreferences.getInstance();
    await p.remove(_kToken);
    await p.remove(_kUser);
    loggedIn.value = false;
  }
}