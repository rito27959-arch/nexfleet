import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/theme.dart';
import '../widgets/aurora_background.dart';
import 'dashboard/dashboard_screen.dart';
import 'drivers/drivers_screen.dart';
import 'maintenance/maintenance_screen.dart';
import 'profile/profile_screen.dart';
import 'vehicles/vehicles_screen.dart';
import 'vidanges/vidanges_screen.dart';

class Shell extends StatefulWidget {
  const Shell({super.key});

  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  int _index = 0;

  final _pages = <Widget>[
    const DashboardScreen(),
    const VehiclesScreen(),
    const VidangesScreen(),
    const MaintenanceScreen(),
    const ProfileScreen(),
  ];

  final _titles = const [
    'Accueil',
    'Véhicules',
    'Vidanges',
    'Entretien',
    'Profil',
  ];

  final _icons = const [
    Icons.space_dashboard_rounded,
    Icons.directions_car_filled_rounded,
    Icons.oil_barrel_rounded,
    Icons.build_circle_rounded,
    Icons.person_rounded,
  ];

  void _select(int i) {
    if (_index == i) return;
    HapticFeedback.selectionClick();
    setState(() => _index = i);
  }

  @override
  Widget build(BuildContext context) {
    return AuroraBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          bottom: false,
          child: IndexedStack(index: _index, children: _pages),
        ),
        bottomNavigationBar: _NexNavBar(
          index: _index,
          titles: _titles,
          icons: _icons,
          onSelect: _select,
        ),
      ),
    );
  }
}

/// Barre de navigation en verre, icônes morphing + pastille d'active.
class _NexNavBar extends StatelessWidget {
  const _NexNavBar({
    required this.index,
    required this.titles,
    required this.icons,
    required this.onSelect,
  });

  final int index;
  final List<String> titles;
  final List<IconData> icons;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(26),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 22, sigmaY: 22),
          child: Container(
            height: 66,
            decoration: BoxDecoration(
              color: const Color(0x0DFFFFFF).withValues(alpha: 0.12),
              border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
              borderRadius: BorderRadius.circular(26),
            ),
            child: Row(
              children: [
                for (var i = 0; i < icons.length; i++)
                  Expanded(
                    child: _NavItem(
                      icon: icons[i],
                      label: titles[i],
                      active: i == index,
                      onTap: () => onSelect(i),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.active,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        curve: Motion.springOut,
        margin: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
        decoration: BoxDecoration(
          gradient: active ? Palette.accentSoft : null,
          borderRadius: BorderRadius.circular(18),
          color: active ? null : Colors.transparent,
          boxShadow: active
              ? [
                  BoxShadow(
                    color: Palette.cyan.withValues(alpha: 0.40),
                    blurRadius: 18,
                    spreadRadius: -2,
                  ),
                ]
              : null,
        ),
        child: TweenAnimationBuilder<double>(
          tween: Tween<double>(begin: 0, end: active ? 1 : 0),
          duration: const Duration(milliseconds: 480),
          curve: Motion.elastic,
          builder: (context, v, child) =>
              Transform.scale(scale: 1 + 0.16 * v, child: child),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 240),
                transitionBuilder: (child, anim) =>
                    ScaleTransition(scale: anim, child: child),
                child: Icon(
                  icon,
                  key: ValueKey(active),
                  size: 23,
                  color: active ? Palette.bg : Palette.textDim,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                maxLines: 1,
                style: TextStyle(
                  fontSize: 9.5,
                  fontWeight: active ? FontWeight.w800 : FontWeight.w500,
                  color: active ? Palette.bg : Palette.textMute,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}