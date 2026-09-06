import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/theme.dart';

/// Fond « aurora » animé : dégradé spatial + halos colorés qui dérivent
/// lentement (+ fine grille). Optimisé (CustomPaint, un seul layer animé).
class AuroraBackground extends StatefulWidget {
  const AuroraBackground({super.key, this.child});

  final Widget? child;

  @override
  State<AuroraBackground> createState() => _AuroraBackgroundState();
}

class _AuroraBackgroundState extends State<AuroraBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(seconds: 26));
  late final Animation<double> _t =
      CurvedAnimation(parent: _c, curve: Curves.linear);

  @override
  void initState() {
    super.initState();
    _c.repeat();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: Stack(
        fit: StackFit.expand,
        children: [
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Palette.bgDeep, Palette.bg, Palette.bgDeep],
              ),
            ),
          ),
          AnimatedBuilder(
            animation: _t,
            builder: (context, _) => CustomPaint(
              painter: _AuroraPainter(progress: _t.value),
              isComplex: true,
              willChange: true,
            ),
          ),
          const IgnorePointer(child: _GridVignette()),
          if (widget.child != null) widget.child!,
        ],
      ),
    );
  }
}

class _AuroraPainter extends CustomPainter {
  _AuroraPainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final t = progress * math.pi * 2;

    final blobs = <(double, double, double, List<Color>)>[
      (0.12, 0.20, 0.55, [Palette.cyan, Palette.teal]),
      (0.85, 0.25, 0.60, [Palette.violet, Palette.magenta]),
      (0.62, 0.85, 0.65, [Palette.indigo, Palette.cyan]),
    ];

    for (var i = 0; i < blobs.length; i++) {
      final (bx, by, r, colors) = blobs[i];
      final dx = math.sin(t + i * 2.3) * 90;
      final dy = math.cos(t * 0.8 + i * 1.7) * 70;
      final cx = w * bx + dx;
      final cy = h * by + dy;
      final radius = math.max(w, h) * r;

      final paint = Paint()
        ..shader = RadialGradient(
          colors: colors.map((c) => c.withValues(alpha: 0.30)).toList(),
          stops: const [0.0, 1.0],
        ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: radius))
        ..blendMode = BlendMode.plus;
      canvas.drawCircle(Offset(cx, cy), radius, paint);
    }
  }

  @override
  bool shouldRepaint(_AuroraPainter old) => old.progress != progress;
}

/// Grille discrète + vignette (statique, jamais repeinte).
class _GridVignette extends StatelessWidget {
  const _GridVignette();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _GridPainter());
  }
}

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final grid = Paint()
      ..color = Palette.cyan.withValues(alpha: 0.035)
      ..strokeWidth = 1;
    const step = 34.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), grid);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    final vignette = Paint()
      ..shader = RadialGradient(
        colors: [
          Colors.transparent,
          Palette.bgDeep.withValues(alpha: 0.55),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
    canvas.drawRect(Offset.zero & size, vignette);
  }

  @override
  bool shouldRepaint(_GridPainter old) => false;
}