import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../config.dart';
import '../core/api_client.dart';
import '../core/app_scope.dart';
import '../core/session.dart';
import '../core/theme.dart';
import '../widgets/aurora_background.dart';
import '../widgets/fx.dart';
import '../widgets/glass.dart';
import '../widgets/toast.dart';
import 'shell.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.session});

  final Session session;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();

  late final AnimationController _shakeCtrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 320),
  );

  bool _obscure = true;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _shakeCtrl.dispose();
    _userCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  void _shake() {
    _shakeCtrl.forward(from: 0);
  }

  /// Amplitude de l'oscillation amortie pendant l'animation.
  double _dampedShake(double t) {
    if (t <= 0 || t >= 1) return 0;
    return math.sin(t * math.pi * 5) * (1 - t) * 18;
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    HapticFeedback.mediumImpact();
    setState(() => _loading = true);
    try {
      final r = await app.api.post('/api/auth/login', {
        'username': _userCtrl.text.trim(),
        'password': _passCtrl.text,
      });
      final user = r['user'] as Map<String, dynamic>;
      await app.session.save(r['token'] as String, user);
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        PageRouteBuilder(
          transitionDuration: const Duration(milliseconds: 700),
          pageBuilder: (_, __, ___) => const Shell(),
          transitionsBuilder: (_, anim, __, child) =>
              FadeTransition(opacity: anim, child: child),
        ),
        (_) => false,
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      HapticFeedback.vibrate();
      _shake();
      showNexToast(context, e.message, kind: Nest.error);
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
      showNexToast(context, 'Serveur injoignable à « ${AppConfig.baseUrl} »',
          kind: Nest.error);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AuroraBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 400),
                child: AnimatedBuilder(
                  animation: _shakeCtrl,
                  builder: (context, child) {
                    final dxFull = _dampedShake(_shakeCtrl.value);
                    return Transform.translate(
                      offset: Offset(dxFull, 0),
                      child: child,
                    );
                  },
                  child: SpringShow(
                    duration: const Duration(milliseconds: 650),
                    child: GlassCard(
                      radius: 30,
                      padding: const EdgeInsets.all(26),
                      child: Form(
                        key: _formKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            _Logo(),
                            const SizedBox(height: 24),
                            const Text(
                              'Connexion',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Palette.text,
                                fontSize: 24,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 6),
                            const Text(
                              'Accédez à votre parc en toute sécurité',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                  color: Palette.textDim, fontSize: 13.5),
                            ),
                            const SizedBox(height: 26),
                            TextFormField(
                              controller: _userCtrl,
                              autocorrect: false,
                              textInputAction: TextInputAction.next,
                              validator: (v) => (v == null || v.trim().isEmpty)
                                  ? 'Identifiant requis'
                                  : null,
                              decoration: const InputDecoration(
                                labelText: 'Identifiant',
                                prefixIcon: Icon(Icons.person_outline_rounded),
                              ),
                            ),
                            const SizedBox(height: 14),
                            TextFormField(
                              controller: _passCtrl,
                              obscureText: _obscure,
                              onFieldSubmitted: (_) => _login(),
                              validator: (v) => (v == null || v.isEmpty)
                                  ? 'Mot de passe requis'
                                  : null,
                              decoration: InputDecoration(
                                labelText: 'Mot de passe',
                                prefixIcon:
                                    const Icon(Icons.lock_outline_rounded),
                                suffixIcon: IconButton(
                                  icon: Icon(_obscure
                                      ? Icons.visibility_outlined
                                      : Icons.visibility_off_outlined),
                                  onPressed: () =>
                                      setState(() => _obscure = !_obscure),
                                ),
                              ),
                            ),
                            const SizedBox(height: 24),
                            GradientButton(
                              label: 'Se connecter',
                              icon: Icons.login_rounded,
                              loading: _loading,
                              onPressed: _login,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              '${AppConfig.baseUrl}',
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                fontSize: 11.5,
                                color: Palette.textMute,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
),
          ),
        ),
      ),
    ),
    );
  }
}

/// Petit logo dégradé du haut de la carte.
class _Logo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        width: 64,
        height: 64,
        decoration: BoxDecoration(
          gradient: Palette.accent,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: Palette.indigo.withValues(alpha: 0.5),
              blurRadius: 30,
            ),
          ],
        ),
        child: const Icon(Icons.directions_car_filled_rounded,
            color: Colors.white, size: 34),
      ),
    );
  }
}