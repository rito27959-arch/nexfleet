import 'package:flutter/material.dart';

import '../core/app_scope.dart';
import '../core/theme.dart';
import '../widgets/aurora_background.dart';
import 'login_screen.dart';
import 'shell.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1500),
  );

  @override
  void initState() {
    super.initState();
    _c.forward();
    _go();
  }

  Future<void> _go() async {
    await app.session.load();
    await Future.delayed(const Duration(milliseconds: 1750));
    if (!mounted) return;
    if (app.session.loggedIn.value) {
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          transitionDuration: const Duration(milliseconds: 650),
          pageBuilder: (_, __, ___) => const Shell(),
          transitionsBuilder: (_, anim, __, child) =>
              FadeTransition(opacity: anim, child: child),
        ),
      );
    } else {
      Navigator.of(context).pushReplacement(
        _fadeTo(LoginScreen(session: app.session)),
      );
    }
  }

  PageRouteBuilder<void> _fadeTo(Widget page) => PageRouteBuilder(
        transitionDuration: const Duration(milliseconds: 650),
        pageBuilder: (_, __, ___) => page,
        transitionsBuilder: (_, anim, __, child) =>
            FadeTransition(opacity: anim, child: child),
      );

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AuroraBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: AnimatedBuilder(
            animation: _c,
            builder: (context, _) {
final logo = CurvedAnimation(
        parent: _c, curve: Interval(0, 0.55, curve: Motion.elastic))
      .value;
final text = CurvedAnimation(
        parent: _c, curve: Interval(0.35, 0.8, curve: Motion.soft))
    .value;
              return Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Transform.scale(
                    scale: 0.8 + 0.2 * logo,
                    child: Opacity(
                      opacity: logo > 1 ? 1.0 : logo,
                      child: Container(
                        width: 96,
                        height: 96,
                        decoration: BoxDecoration(
                          gradient: Palette.accent,
                          borderRadius: BorderRadius.circular(28),
                          boxShadow: [
                            BoxShadow(
                              color: Palette.indigo.withValues(alpha: 0.55),
                              blurRadius: 40,
                              spreadRadius: -4,
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.directions_car_filled_rounded,
                          color: Colors.white,
                          size: 52,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 26),
                  Opacity(
                    opacity: text,
                    child: Transform.translate(
                      offset: Offset(0, 12 * (1 - text)),
                      child: const Column(
                        children: [
                          Text(
                            'NexFleet',
                            style: TextStyle(
                              color: Palette.text,
                              fontSize: 34,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 2.5,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'GESTION DE PARC AUTOMOBILE',
                            style: TextStyle(
                              color: Palette.textDim,
                              fontSize: 11.5,
                              letterSpacing: 3.2,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}