import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../core/app_scope.dart';
import '../../core/haptics.dart';
import '../../core/models.dart';
import '../../core/theme.dart';
import '../../utils/format.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/fx.dart';
import '../../widgets/glass.dart';
import '../../widgets/pressable.dart';
import '../../widgets/toast.dart';
import 'vidange_form_sheet.dart';

class VidangesScreen extends StatefulWidget {
  const VidangesScreen({super.key});

  @override
  State<VidangesScreen> createState() => _VidangesScreenState();
}

class _VidangesScreenState extends State<VidangesScreen> {
  List<Vidange> _vidanges = [];
  VidangeStats? _stats;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        app.api.get('/api/vidanges'),
        app.api.get('/api/vidanges/stats'),
      ]);
      if (!mounted) return;
      setState(() {
        _vidanges = [
          for (final v in (results[0]['vidanges'] as List? ?? const []))
            if (v is Map<String, dynamic>) Vidange.fromJson(v)
        ];
        _stats = VidangeStats.fromJson(results[1]);
        _loading = false;
        _error = null;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.message;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Serveur injoignable.';
      });
    }
  }

  Future<void> _add() async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const VidangeFormSheet(),
    );
    if (ok == true) {
      showNexToast(context, 'Vidange enregistrée', kind: Nest.success);
      _load();
    }
  }

  Future<void> _edit(Vidange v) async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => VidangeFormSheet(vidange: v),
    );
    if (ok == true) {
      showNexToast(context, 'Vidange mise à jour', kind: Nest.success);
      _load();
    }
  }

  Future<void> _delete(Vidange v) async {
    final ok = await _confirm(context, v.vehicleLabel);
    if (ok != true || !mounted) return;
    try {
      await app.api.delete('/api/vidanges/${v.id}');
      if (!mounted) return;
      showNexToast(context, 'Vidange supprimée', kind: Nest.success);
      _load();
    } on ApiException catch (e) {
      if (!mounted) return;
      showNexToast(context, e.message, kind: Nest.error);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Column(
          children: [
            const _Title(),
            if (_stats != null) _StatsStrip(stats: _stats!),
            Expanded(
              child: _loading
                  ? const ScreenSkeleton()
                  : _error != null
                      ? EmptyState(
                          icon: Icons.cloud_off_rounded,
                          title: _error!,
                          action: GradientButton(
                            label: 'Réessayer',
                            onPressed: _load,
                            expand: false,
                          ),
                        )
                      : _vidanges.isEmpty
                          ? const EmptyState(
                              icon: Icons.oil_barrel_rounded,
                              title: 'Aucune vidange',
                              subtitle: 'Ajoutez votre premier suivi.',
                            )
                          : RefreshIndicator(
                              color: Palette.cyan,
                              backgroundColor: const Color(0xFF0B1120),
                              onRefresh: _load,
                              child: ListView.builder(
                                physics:
                                    const AlwaysScrollableScrollPhysics(),
                                padding: const EdgeInsets.fromLTRB(
                                    16, 10, 16, 110),
                                itemCount: _vidanges.length,
                                itemBuilder: (context, i) => _VidangeTile(
                                  vidange: _vidanges[i],
                                  onEdit: () => _edit(_vidanges[i]),
                                  onDelete: app.session.isAdmin
                                      ? () => _delete(_vidanges[i])
                                      : null,
                                ),
                              ),
                            ),
            ),
          ],
        ),
        _addVidanges(context),
      ],
    );
  }

  Widget _addVidanges(BuildContext context) {
    return Positioned(
      right: 18,
      bottom: 8,
      child: ScaleTap(
        haptic: false,
        onTap: () {
          pulseMedium();
          _add();
        },
        child: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            gradient: Palette.accent,
            borderRadius: BorderRadius.circular(19),
            boxShadow: [
              BoxShadow(
                color: Palette.indigo.withValues(alpha: 0.5),
                blurRadius: 24,
              ),
            ],
          ),
          child: const Icon(Icons.add_rounded, color: Colors.white, size: 26),
        ),
      ),
    );
  }
}

Future<bool?> _confirm(BuildContext context, String label) {
  return showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      backgroundColor: const Color(0xFF111830),
      title: const Text('Supprimer ?',
          style: TextStyle(color: Palette.text, fontSize: 18)),
      content: Text('Vidange pour « $label ».', style: const TextStyle(color: Palette.textDim)),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Annuler'),
        ),
        TextButton(
          onPressed: () => Navigator.of(context).pop(true),
          child: const Text('Supprimer',
              style: TextStyle(color: Palette.danger)),
        ),
      ],
    ),
  );
}

class _Title extends StatelessWidget {
  const _Title();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.fromLTRB(18, 16, 18, 4),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Text(
          'Vidanges',
          style: TextStyle(
            color: Palette.text,
            fontSize: 24,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _StatsStrip extends StatelessWidget {
  const _StatsStrip({required this.stats});

  final VidangeStats stats;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 84,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 6),
        children: [
          _Stat(
            icon: Icons.oil_barrel_rounded,
            color: Palette.cyan,
            value: '${stats.total}',
            label: 'Vidanges',
          ),
          _Stat(
            icon: Icons.calendar_today_outlined,
            color: Palette.violet,
            value: '${stats.thisYear}',
            label: 'Cette année',
          ),
          _Stat(
            icon: Icons.payments_outlined,
            color: Palette.warning,
            value: inr(stats.costTotal),
            label: 'Coût total',
          ),
          _Stat(
            icon: Icons.alarm_rounded,
            color: Palette.danger,
            value: '${stats.forecast.where((f) => f.due).length}',
            label: 'À faire',
          ),
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final Color color;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: GlassCard(
        radius: 18,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 10),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Icon(icon, color: color, size: 17),
            ),
            const SizedBox(width: 10),
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: TextStyle(
                    color: color,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  label,
                  style: const TextStyle(
                      color: Palette.textMute, fontSize: 10.5),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _VidangeTile extends StatelessWidget {
  const _VidangeTile({
    required this.vidange,
    required this.onEdit,
    this.onDelete,
  });

  final Vidange vidange;
  final VoidCallback onEdit;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final enabled = vidange.consommables.where((c) => c.on).toList();
    final last = enabled.length <= 2 ? enabled : enabled.take(2).toList();
    final more = enabled.length - last.length;

    Widget tile = GlassCard(
      radius: 20,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Palette.cyan.withValues(alpha: 0.3),
                      Palette.violet.withValues(alpha: 0.22),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(Icons.oil_barrel_rounded,
                    color: Palette.cyan, size: 21),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      vidange.vehicleLabel,
                      style: const TextStyle(
                        color: Palette.text,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${frDate(vidange.date)}${vidange.huile.isNotEmpty ? ' · ${vidange.huile}' : ''}',
                      style: const TextStyle(
                          color: Palette.textDim, fontSize: 12.5),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    money(vidange.cout),
                    style: const TextStyle(
                      color: Palette.warning,
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  if (vidange.km > 0)
                    Text(
                      '${inr(vidange.km)} km',
                      style: const TextStyle(
                          color: Palette.textMute, fontSize: 11.5),
                    ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          Divider(color: Colors.white.withValues(alpha: 0.06), height: 1),
          const SizedBox(height: 10),
          Row(
            children: [
              _KmChip(
                icon: Icons.my_location_rounded,
                label: 'Compteur',
                value: '${inr(vidange.km)}',
                color: Palette.textDim,
              ),
              const SizedBox(width: 8),
              _KmChip(
                icon: Icons.trending_up_rounded,
                label: 'Intervalle',
                value: '${inr(vidange.kmInterval)} km',
                color: Palette.textMute,
              ),
              const SizedBox(width: 8),
              _KmChip(
                icon: Icons.flag_rounded,
                label: 'Prochaine',
                value: '${inr(vidange.prochaineKm)} km',
                color: Palette.cyan,
              ),
            ],
          ),
          if (enabled.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final c in last)
                  _Chip(
                    label: c.label,
                    color: Palette.success,
                  ),
                if (more > 0)
                  _Chip(label: '+$more', color: Palette.textDim),
              ],
            ),
          ],
        ],
      ),
    );

    if (onDelete != null) {
      tile = Dismissible(
        key: ValueKey('vg-${vidange.id}'),
        direction: DismissDirection.endToStart,
        confirmDismiss: (_) async => true,
        onDismissed: (_) => onDelete!(),
        background: Container(
          margin: const EdgeInsets.only(bottom: 12),
          alignment: Alignment.centerRight,
          padding: const EdgeInsets.only(right: 22),
          decoration: BoxDecoration(
            color: Palette.danger.withValues(alpha: 0.9),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Icon(Icons.delete_rounded, color: Colors.white),
        ),
        child: ScaleTap(onTap: onEdit, child: tile),
      );
    } else {
      tile = ScaleTap(onTap: onEdit, child: tile);
    }
    return tile;
  }
}

class _KmChip extends StatelessWidget {
  const _KmChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(11),
        ),
        child: Row(
          children: [
            Icon(icon, color: color, size: 13),
            const SizedBox(width: 5),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label,
                      style: const TextStyle(
                          color: Palette.textMute, fontSize: 9.5)),
                  Text(value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: color,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w800,
                      )),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 10.5,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}