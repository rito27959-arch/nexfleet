import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme.dart';

/// Micro-interaction à la iOS : la surface s'enfonce vite au toucher puis
/// « reprend » avec un ressort (easeOutBack) au relâchement, accompagnée d'un
/// retour haptique léger. Aucun ripple — purement gestuel, comme les apps
/// natives modernes.
class ScaleTap extends StatefulWidget {
  const ScaleTap({
    super.key,
    required this.child,
    this.onTap,
    this.scale = 0.96,
    this.haptic = true,
    this.enabled = true,
  });

  final Widget child;
  final VoidCallback? onTap;
  final double scale;
  final bool haptic;
  final bool enabled;

  @override
  State<ScaleTap> createState() => _ScaleTapState();
}

class _ScaleTapState extends State<ScaleTap> {
  bool _down = false;

  void _set(bool value) {
    if (!widget.enabled) return;
    setState(() => _down = value);
  }

  void _onTapDown(TapDownDetails _) {
    if (widget.onTap == null) return;
    if (widget.haptic) HapticFeedback.lightImpact();
    _set(true);
  }

  void _onTapCancel() => _set(false);

  void _onTapUp(TapUpDetails _) => _set(false);

  @override
  Widget build(BuildContext context) {
    final pressable = widget.enabled && widget.onTap != null;
    return GestureDetector(
      onTapDown: pressable ? _onTapDown : null,
      onTapUp: pressable ? _onTapUp : null,
      onTapCancel: pressable ? _onTapCancel : null,
      onTap: widget.enabled ? widget.onTap : null,
      behavior: HitTestBehavior.opaque,
      child: AnimatedScale(
        scale: _down ? widget.scale : 1,
        duration: _down
            ? const Duration(milliseconds: 80)
            : const Duration(milliseconds: 380),
        curve: _down ? Motion.press : Motion.springOut,
        child: widget.child,
      ),
    );
  }
}