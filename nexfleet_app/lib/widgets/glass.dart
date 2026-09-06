import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme.dart';
import 'pressable.dart';

/// Carte en verre dépoli avec bord lumineux.
class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    this.child,
    this.padding = const EdgeInsets.all(16),
    this.margin,
    this.radius = 22,
    this.glow,
    this.onTap,
  });

  final Widget? child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final double radius;
  final Color? glow;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final card = ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.white.withValues(alpha: 0.09),
                Colors.white.withValues(alpha: 0.04),
              ],
            ),
            border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
            boxShadow: [
              if (glow != null)
                BoxShadow(
                  color: glow!.withValues(alpha: 0.22),
                  blurRadius: 36,
                  spreadRadius: -6,
                ),
            ],
          ),
          padding: padding,
          child: child,
        ),
      ),
    );
    if (onTap == null) return card;
    return GestureDetector(onTap: onTap, child: card);
  }
}

/// Bouton dégradé (peut être pressé) avec retour haptique et micro-scale.
class GradientButton extends StatefulWidget {
  const GradientButton({
    super.key,
    required this.label,
    this.icon,
    this.onPressed,
    this.gradient = Palette.accent,
    this.loading = false,
    this.height = 52,
    this.expand = true,
  });

  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final Gradient gradient;
  final bool loading;
  final double height;
  final bool expand;

  @override
  State<GradientButton> createState() => _GradientButtonState();
}

class _GradientButtonState extends State<GradientButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ac = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 140),
    lowerBound: 0,
    upperBound: 1,
  );

  bool _down = false;

  void _press(bool down) {
    if (widget.onPressed == null || widget.loading) return;
    setState(() => _down = down);
    if (down) {
      HapticFeedback.lightImpact();
      _ac.forward();
    } else {
      _ac.reverse();
    }
  }

  @override
  void dispose() {
    _ac.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final content = AnimatedBuilder(
      animation: _ac,
      builder: (context, _) {
        final scale = 1 - 0.04 * _ac.value;
        return Transform.scale(
          scale: scale,
          child: Container(
            height: widget.height,
            decoration: BoxDecoration(
              gradient: widget.gradient,
              borderRadius: BorderRadius.circular(widget.height / 2),
              boxShadow: [
                BoxShadow(
                  color: Palette.indigo.withValues(alpha: 0.45),
                  blurRadius: 22,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            alignment: Alignment.center,
            child: widget.loading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.4,
                      color: Colors.white,
                    ),
                  )
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (widget.icon != null) ...[
                        Icon(widget.icon, color: Colors.white, size: 19),
                        const SizedBox(width: 9),
                      ],
                      Text(
                        widget.label,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ],
                  ),
          ),
        );
      },
    );

    final inner = GestureDetector(
      onTapDown: (_) => _press(true),
      onTapUp: (_) => _press(false),
      onTapCancel: () => _press(false),
      onTap: widget.loading ? null : widget.onPressed,
      behavior: HitTestBehavior.opaque,
      child: content,
    );

    if (!widget.expand) return inner;
    return SizedBox(width: double.infinity, child: inner);
  }
}

/// Puce interactive (filtres, statuts) avec animation de sélection.
class FilterChipNex extends StatelessWidget {
  const FilterChipNex({
    super.key,
    required this.label,
    required this.selected,
    this.onTap,
    this.count,
    this.color,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;
  final String? count;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? (selected ? Palette.cyan : null);
    return ScaleTap(
      scale: 0.92,
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Motion.springOut,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Motion.soft,
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 8),
          decoration: BoxDecoration(
            gradient: selected
                ? LinearGradient(colors: [
                    c!.withValues(alpha: 0.28),
                    c.withValues(alpha: 0.12),
                  ])
                : null,
            color: selected ? null : Colors.white.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(30),
            border: Border.all(
              color: selected
                  ? c!.withValues(alpha: 0.8)
                  : Colors.white.withValues(alpha: 0.10),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (selected) ...[
                    Icon(Icons.check_rounded, size: 14, color: c),
                    const SizedBox(width: 5),
                  ],
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                      color: selected ? c : Palette.textDim,
                    ),
                  ),
                  if (count != null) ...[
                    const SizedBox(width: 6),
                    Text(
                      count!,
                      style: const TextStyle(
                        fontSize: 11.5,
                        color: Palette.textMute,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
  }
}