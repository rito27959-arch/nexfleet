import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/theme.dart';

/// Anneau (donut) animé à la construction, avec centre.
class Donut extends StatefulWidget {
  const Donut({
    super.key,
    required this.segments,
    this.size = 150,
    this.thickness = 15,
    this.center,
  });

  final List<({double value, Color color})> segments;
  final double size;
  final double thickness;
  final Widget? center;

  @override
  State<Donut> createState() => _DonutState();
}

class _DonutState extends State<Donut> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );

  @override
  void initState() {
    super.initState();
    _c.forward();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        final t = CurvedAnimation(parent: _c, curve: Motion.soft).value;
        return SizedBox(
          width: widget.size,
          height: widget.size,
          child: CustomPaint(
            painter: _DonutPainter(
              segments: widget.segments,
              progress: t,
              thickness: widget.thickness,
            ),
            child: Center(child: widget.center),
          ),
        );
      },
    );
  }
}

class _DonutPainter extends CustomPainter {
  _DonutPainter({
    required this.segments,
    required this.progress,
    required this.thickness,
  });

  final List<({double value, Color color})> segments;
  final double progress;
  final double thickness;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final total = segments.fold<double>(
        0, (acc, s) => acc + (s.value < 0 ? 0 : s.value));
    if (total <= 0) {
      canvas.drawCircle(
        rect.center,
        size.width / 2 - thickness / 2,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = thickness
          ..color = Colors.white.withValues(alpha: 0.06),
      );
      return;
    }
    final base = -math.pi / 2;
    var start = base;
    for (final seg in segments) {
      final frac = (seg.value < 0 ? 0 : seg.value) / total * progress;
      final sweep = frac * math.pi * 2;
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = thickness
        ..strokeCap = StrokeCap.round
        ..color = seg.color;
      canvas.drawArc(rect.deflate(thickness / 2), start, sweep, false, paint);
      start += sweep;
    }
  }

  @override
  bool shouldRepaint(_DonutPainter old) =>
      old.progress != progress || old.segments != segments;
}

/// Barres verticales animées (contrôles / mois).
class Bars extends StatelessWidget {
  const Bars({
    super.key,
    required this.values,
    this.labels,
    this.barColor = Palette.cyan,
    this.height = 120,
  });

  final List<double> values;
  final List<String>? labels;
  final Color barColor;
  final double height;

  @override
  Widget build(BuildContext context) {
    final max = values.fold<double>(0, math.max);
    return SizedBox(
      height: height,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (var i = 0; i < values.length; i++) ...[
            if (i > 0) const SizedBox(width: 8),
            Expanded(
              child: _Bar(
                value: values[i],
                max: max,
                color: i == values.length - 1 ? Palette.violet : barColor,
                label: labels != null && i < labels!.length ? labels![i] : null,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Bar extends StatelessWidget {
  const _Bar({required this.value, required this.max, required this.color, this.label});

  final double value;
  final double max;
  final Color color;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final frac = max <= 0 ? 0.0 : (value / max);
    return Column(
      children: [
        Expanded(
          child: Align(
            alignment: Alignment.bottomCenter,
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: frac),
              duration: const Duration(milliseconds: 900),
              curve: Motion.soft,
              builder: (context, f, _) {
                return FractionallySizedBox(
                  heightFactor: f,
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          color.withValues(alpha: 0.95),
                          color.withValues(alpha: 0.25),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(8),
                      boxShadow: [
                        BoxShadow(
                          color: color.withValues(alpha: 0.35),
                          blurRadius: 10,
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        if (label != null) ...[
          const SizedBox(height: 6),
          Text(
            label!,
            style: const TextStyle(fontSize: 10, color: Palette.textMute),
          ),
        ],
      ],
    );
  }
}

/// Mini-bandeau de progression « restant » (km/jours avant échéance).
class Gauge extends StatelessWidget {
  const Gauge({
    super.key,
    required this.frac,
    required this.color,
  });

  final double frac;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(6),
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: frac < 0 ? 0 : (frac > 1 ? 1 : frac)),
        duration: const Duration(milliseconds: 800),
        curve: Motion.soft,
        builder: (context, f, _) => LinearProgressIndicator(
          value: f,
          minHeight: 5,
          backgroundColor: Colors.white.withValues(alpha: 0.07),
          valueColor: AlwaysStoppedAnimation(color),
        ),
      ),
    );
  }
}