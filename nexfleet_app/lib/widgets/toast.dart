import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme.dart';

enum Nest {
  success(Palette.success),
  error(Palette.danger),
  info(Palette.cyan);

  const Nest(this.color);
  final Color color;
}

/// Affichage d'un toast type iOS : entre par en haut avec un ressort,
/// ligne de progression puis disparition élastique.
void showNexToast(BuildContext context, String message,
    {Nest kind = Nest.info}) {
  final overlay = Overlay.of(context);
  late final OverlayEntry entry;
  entry = OverlayEntry(
    builder: (context) => Positioned(
      left: 20,
      right: 20,
      top: MediaQuery.paddingOf(context).top + 10,
      child: _ToastCard(
        message: message,
        kind: kind,
        onDone: () => entry.remove(),
      ),
    ),
  );
  overlay.insert(entry);
}

class _ToastCard extends StatefulWidget {
  const _ToastCard({
    required this.message,
    required this.kind,
    required this.onDone,
  });

  final String message;
  final Nest kind;
  final VoidCallback onDone;

  @override
  State<_ToastCard> createState() => _ToastCardState();
}

class _ToastCardState extends State<_ToastCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _show = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 460),
    reverseDuration: const Duration(milliseconds: 300),
  );

  late final AnimationController _life = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2600),
  );

  @override
  void initState() {
    super.initState();
    _show.forward();
    _life.forward();
    Future.delayed(_life.duration!, () async {
      if (!mounted) return;
      await _show.reverse();
      if (mounted) widget.onDone();
    });
  }

  @override
  void dispose() {
    _show.dispose();
    _life.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: FadeTransition(
        opacity: CurvedAnimation(parent: _show, curve: Motion.soft),
        child: SlideTransition(
          position: Tween(begin: const Offset(0, -1.4), end: Offset.zero)
              .animate(CurvedAnimation(parent: _show, curve: Motion.elastic)),
          child: AnimatedBuilder(
            animation: _life,
            builder: (context, child) => Stack(
              clipBehavior: Clip.none,
              children: [
                child!,
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: -6,
                  child: FractionallySizedBox(
                    widthFactor: 1 - _life.value,
                    child: Container(
                      height: 3,
                      decoration: BoxDecoration(
                        color: widget.kind.color,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            child: Container(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 13),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [
                  widget.kind.color.withValues(alpha: 0.30),
                  const Color(0x5505070F),
                ]),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: widget.kind.color.withValues(alpha: 0.8),
                ),
                boxShadow: [
                  BoxShadow(
                    color: widget.kind.color.withValues(alpha: 0.30),
                    blurRadius: 26,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Icon(
                    switch (widget.kind) {
                      Nest.success => Icons.check_circle_rounded,
                      Nest.error => Icons.error_rounded,
                      Nest.info => Icons.info_rounded,
                    },
                    color: widget.kind.color,
                    size: 21,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      widget.message,
                      style: const TextStyle(
                        color: Palette.text,
                        fontSize: 13.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

void hapticHit() => HapticFeedback.lightImpact();
void hapticTap() => HapticFeedback.selectionClick();