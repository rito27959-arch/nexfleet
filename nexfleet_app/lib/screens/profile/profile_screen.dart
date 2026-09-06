import 'package:flutter/material.dart';

import '../../config.dart';
import '../../core/api_client.dart';
import '../../core/app_scope.dart';
import '../../core/haptics.dart';
import '../../core/theme.dart';
import '../../widgets/fx.dart';
import '../../widgets/glass.dart';
import '../../widgets/pressable.dart';
import '../../widgets/toast.dart';
import '../login_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _oldPass = TextEditingController();
  final _newPass = TextEditingController();
  final _newPass2 = TextEditingController();
  bool _changingPass = false;
  bool _loggingOut = false;

  @override
  void dispose() {
    _oldPass.dispose();
    _newPass.dispose();
    _newPass2.dispose();
    super.dispose();
  }

  Future<void> _changePassword() async {
    final pw = _newPass.text;
    if (pw.length < 8 || !pw.contains(RegExp(r'[0-9]'))) {
      showNexToast(
          context, 'Nouveau mot de passe : 8 caractères minimum avec un chiffre.',
          kind: Nest.error);
      return;
    }
    if (_newPass.text != _newPass2.text) {
      showNexToast(context, 'Les mots de passe ne correspondent pas',
          kind: Nest.error);
      return;
    }
    setState(() => _changingPass = true);
    try {
      await app.api.put('/api/auth/password', {
        'old_password': _oldPass.text,
        'new_password': _newPass.text,
      });
      if (!mounted) return;
      _oldPass.clear();
      _newPass.clear();
      _newPass2.clear();
      showNexToast(context, 'Mot de passe modifié', kind: Nest.success);
    } on ApiException catch (e) {
      if (!mounted) return;
      showNexToast(context, e.message, kind: Nest.error);
    } catch (_) {
      if (!mounted) return;
      showNexToast(context, 'Impossible de joindre le serveur',
          kind: Nest.error);
    } finally {
      if (mounted) setState(() => _changingPass = false);
    }
  }

  Future<void> _logout() async {
    pulseMedium();
    setState(() => _loggingOut = true);
    await app.session.clear();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      PageRouteBuilder(
        transitionDuration: const Duration(milliseconds: 600),
        pageBuilder: (_, __, ___) => LoginScreen(session: app.session),
        transitionsBuilder: (_, anim, __, child) =>
            FadeTransition(opacity: anim, child: child),
      ),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = app.session.user;
    final username = user?['username'] as String? ?? 'Utilisateur';
    final email = user?['email'] as String? ?? '';
    final role = app.session.role;
    final roleLabel = role == 'admin' ? 'Administrateur' : 'Utilisateur';

    return SpringShow(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(18, 16, 18, 100),
        children: [
        const Text(
          'Profil',
          style: TextStyle(
            color: Palette.text,
            fontSize: 24,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 18),
        GlassCard(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Container(
                width: 58,
                height: 58,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  gradient: Palette.accent,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Palette.indigo.withValues(alpha: 0.5),
                      blurRadius: 24,
                    ),
                  ],
                ),
                child: Text(
                  username.characters.first.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      username,
                      style: const TextStyle(
                        color: Palette.text,
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      email,
                      style: const TextStyle(
                          color: Palette.textDim, fontSize: 13),
                    ),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 9, vertical: 3),
                      decoration: BoxDecoration(
                        color: Palette.cyan.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        roleLabel,
                        style: const TextStyle(
                          color: Palette.cyan,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GlassCard(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Serveur connecté',
                style: TextStyle(
                  color: Palette.text,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.dns_rounded,
                      color: Palette.success, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: SelectableText(
                      AppConfig.baseUrl,
                      style: const TextStyle(
                          color: Palette.textDim, fontSize: 13),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              const Text(
                'Pour déployer vers une API distante : configurez '
                'l’URL à la compilation avec '
                '--dart-define=API_URL=https://…',
                style: TextStyle(color: Palette.textMute, fontSize: 12),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GlassCard(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Changer le mot de passe',
                style: TextStyle(
                  color: Palette.text,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: _oldPass,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Mot de passe actuel',
                  prefixIcon: Icon(Icons.lock_outline_rounded, size: 19),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _newPass,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Nouveau mot de passe',
                  prefixIcon: Icon(Icons.lock_reset_rounded, size: 19),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _newPass2,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Confirmer le nouveau',
                  prefixIcon: Icon(Icons.lock_reset_rounded, size: 19),
                ),
              ),
              const SizedBox(height: 16),
              GradientButton(
                label: 'Mettre à jour',
                icon: Icons.check_rounded,
                loading: _changingPass,
                onPressed: _changePassword,
                expand: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: 22),
        ScaleTap(
          haptic: false,
          onTap: _loggingOut ? null : _logout,
          child: Container(
            height: 52,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Palette.danger.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: Palette.danger.withValues(alpha: 0.4),
              ),
            ),
            child: _loggingOut
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        color: Palette.danger, strokeWidth: 2.4),
                  )
                : const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.logout_rounded,
                          color: Palette.danger, size: 20),
                      SizedBox(width: 9),
                      Text(
                        'Se déconnecter',
                        style: TextStyle(
                          color: Palette.danger,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
      ],
      ),
    );
  }
}