import 'package:flutter/material.dart';

import '../core/theme.dart';
import 'fx.dart';

/// État vide élégant (aucune donnée, recherche sans résultat) :
/// icône qui « respire » et colonne qui entre avec un ressort.
class EmptyState extends StatefulWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    this.action,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final Widget? action;

  @override
  State<EmptyState> createState() => _EmptyStateState();
}

class _EmptyStateState extends State<EmptyState>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2200),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SpringShow(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedBuilder(
                animation: _c,
                builder: (context, child) => Transform.scale(
                  scale: 1 + 0.05 * _c.value,
                  child: Container(
                    width: 76,
                    height: 76,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          Palette.cyan.withValues(alpha: 0.22 + 0.08 * _c.value),
                          Palette.violet.withValues(alpha: 0.12),
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Palette.cyan.withValues(alpha: 0.16),
                          blurRadius: 30,
                        ),
                      ],
                    ),
                    child: Icon(
                      widget.icon,
                      color: Palette.cyan.withValues(alpha: 0.9),
                      size: 30,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              Text(
                widget.title,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Palette.text,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (widget.subtitle != null) ...[
                const SizedBox(height: 6),
                Text(
                  widget.subtitle!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: Palette.textDim, fontSize: 13.5),
                ),
              ],
              if (widget.action != null) ...[
                const SizedBox(height: 22),
                widget.action!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}