import 'package:flutter/material.dart';

import '../core/theme.dart';

/// Compteur animé : passe de 0 à [value] avec une courbe « respire ».
class AnimatedNumber extends StatefulWidget {
  const AnimatedNumber(
    this.value, {
    super.key,
    this.duration = const Duration(milliseconds: 1100),
    this.style,
  });

  final double value;
  final Duration duration;
  final TextStyle? style;

  @override
  State<AnimatedNumber> createState() => _AnimatedNumberState();
}

class _AnimatedNumberState extends State<AnimatedNumber>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: widget.duration);
  late Animation<double> _v;
  late double _from;

  @override
  void initState() {
    super.initState();
    _from = 0;
    _v = Tween(begin: _from, end: widget.value)
        .animate(CurvedAnimation(parent: _c, curve: Motion.soft));
    _c.forward();
  }

  @override
  void didUpdateWidget(covariant AnimatedNumber old) {
    super.didUpdateWidget(old);
    if (old.value != widget.value) {
      _from = old.value;
      _c.reset();
      _v = Tween(begin: _from, end: widget.value)
          .animate(CurvedAnimation(parent: _c, curve: Motion.soft));
      _c.forward();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _v,
      builder: (context, _) => Text(
        _v.value.toStringAsFixed(0),
        style: widget.style,
      ),
    );
  }
}

/// Squelette de chargement (shimmer).
class Skeleton extends StatefulWidget {
  const Skeleton({
    super.key,
    this.width,
    this.height = 14,
    this.radius = 8,
  });

  final double? width;
  final double height;
  final double radius;

  @override
  State<Skeleton> createState() => _SkeletonState();
}

class _SkeletonState extends State<Skeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 1500))
    ..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, child) {
        final d = _c.value;
        return Container(
          width: widget.width,
          height: widget.height,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(widget.radius),
          ),
          child: ShaderMask(
            blendMode: BlendMode.srcATop,
            shaderCallback: (bounds) => LinearGradient(
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
              colors: const [
                Color(0x00FFFFFF),
                Color(0x66FFFFFF),
                Color(0x00FFFFFF),
              ],
              stops: const [0.35, 0.5, 0.65],
              transform: _SlideGradientTransform(d),
            ).createShader(bounds),
            child: child,
          ),
        );
      },
      child: ColoredBox(color: Colors.white.withValues(alpha: 0.08)),
    );
  }
}

/// Transforme le dégradé shimmer le long de la surface (balayage).
class _SlideGradientTransform extends GradientTransform {
  const _SlideGradientTransform(this.value);

  final double value;

  @override
  Matrix4? transform(Rect bounds, {TextDirection? textDirection}) {
    final x = (value * 3 - 0.5) * bounds.width;
    return Matrix4.translationValues(x, 0, 0);
  }
}

/// Boîte squelettique pour un écran en chargement.
class ScreenSkeleton extends StatelessWidget {
  const ScreenSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Skeleton(width: 160, height: 26),
          SizedBox(height: 18),
          Skeleton(height: 96, radius: 22),
          SizedBox(height: 16),
          Skeleton(height: 96, radius: 22),
          SizedBox(height: 16),
          Skeleton(height: 140, radius: 22),
        ],
      ),
    );
  }
}

/// Liste avec entrée en cascade (staggered entrance).
class Staggered extends StatelessWidget {
  const Staggered({
    super.key,
    required this.itemCount,
    required this.itemBuilder,
    this.delay = const Duration(milliseconds: 45),
  });

  final int itemCount;
  final Widget Function(BuildContext, int) itemBuilder;
  final Duration delay;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < itemCount; i++)
          _Item(
            index: i,
            delay: delay,
            child: itemBuilder(context, i),
          ),
      ],
    );
  }
}

class _Item extends StatefulWidget {
  const _Item({required this.index, required this.delay, required this.child});

  final int index;
  final Duration delay;
  final Widget child;

  @override
  State<_Item> createState() => _ItemState();
}

class _ItemState extends State<_Item> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 460),
  );

  @override
  void initState() {
    super.initState();
    Future.delayed(widget.delay * widget.index, () {
      if (mounted) _c.forward();
    });
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
      builder: (context, child) {
        final t = CurvedAnimation(parent: _c, curve: Motion.soft).value;
        return Opacity(
          opacity: t,
          child: Transform.translate(
            offset: Offset(0, 16 * (1 - t)),
            child: child,
          ),
        );
      },
      child: widget.child,
    );
  }
}

/// Entrée « pop » à la iOS : fondu + échelle élastique (léger overshoot).
class SpringShow extends StatefulWidget {
  const SpringShow({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.duration = const Duration(milliseconds: 600),
  });

  final Widget child;
  final Duration delay;
  final Duration duration;

  @override
  State<SpringShow> createState() => _SpringShowState();
}

class _SpringShowState extends State<SpringShow>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: widget.duration,
  );

  @override
  void initState() {
    super.initState();
    if (widget.delay == Duration.zero) {
      _c.forward();
    } else {
      Future.delayed(widget.delay, () {
        if (mounted) _c.forward();
      });
    }
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
      builder: (context, child) {
        final t = CurvedAnimation(parent: _c, curve: Motion.elastic).value;
        final fade = t < 0 ? 0.0 : (t > 1 ? 1.0 : t);
        return Opacity(
          opacity: fade,
          child: Transform.scale(scale: 0.96 + 0.04 * t, child: child),
        );
      },
      child: widget.child,
    );
  }
}