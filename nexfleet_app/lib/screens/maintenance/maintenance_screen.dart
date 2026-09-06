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
import 'maintenance_form_sheet.dart';

class MaintenanceScreen extends StatefulWidget {
  const MaintenanceScreen({super.key});

  @override
  State<MaintenanceScreen> createState() => _MaintenanceScreenState();
}

class _MaintenanceScreenState extends State<MaintenanceScreen> {
  List<MaintenanceItem> _items = [];
  bool _loading = true;
  String? _error;
  double _total = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await app.api.get('/api/maintenance');
      if (!mounted) return;
      final items = [
        for (final m in (r['maintenance'] as List? ?? const []))
          if (m is Map<String, dynamic>) MaintenanceItem.fromJson(m)
      ];
      setState(() {
        _items = items;
        _total = items.fold<double>(0, (a, m) => a + m.cout);
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
      builder: (_) => const MaintenanceFormSheet(),
    );
    if (ok == true) {
      showNexToast(context, 'Intervention enregistrée', kind: Nest.success);
      _load();
    }
  }

  Future<void> _delete(MaintenanceItem m) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF111830),
        title: const Text('Supprimer ?',
            style: TextStyle(color: Palette.text, fontSize: 18)),
        content: Text('${m.type} pour « ${m.vehicleLabel} ».',
            style: const TextStyle(color: Palette.textDim)),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Annuler')),
          TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Supprimer',
                  style: TextStyle(color: Palette.danger))),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await app.api.delete('/api/maintenance/${m.id}');
      if (!mounted) return;
      showNexToast(context, 'Intervention supprimée', kind: Nest.success);
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
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 16, 18, 4),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Entretien',
                      style: TextStyle(
                        color: Palette.text,
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 11, vertical: 6),
                    decoration: BoxDecoration(
                      color: Palette.warning.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: Palette.warning.withValues(alpha: 0.3),
                      ),
                    ),
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 250),
                      child: Text(
                        money(_total),
                        key: ValueKey(_total),
                        style: const TextStyle(
                          color: Palette.warning,
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
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
                      : _items.isEmpty
                          ? const EmptyState(
                              icon: Icons.build_rounded,
                              title: 'Aucune intervention',
                              subtitle: 'Enregistrez la première.',
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
                                itemCount: _items.length,
                                itemBuilder: (context, i) => Staggered(
                                  itemCount: 1,
                                  itemBuilder: (_, __) =>
                                      _MaintenanceTile(
                                        item: _items[i],
                                        onDelete: app.session.isAdmin
                                            ? () => _delete(_items[i])
                                            : null,
                                      ),
                                ),
                              ),
                            ),
            ),
          ],
        ),
        Positioned(
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
              child: const Icon(Icons.add_rounded,
                  color: Colors.white, size: 26),
            ),
          ),
        ),
      ],
    );
  }
}

class _MaintenanceTile extends StatelessWidget {
  const _MaintenanceTile({required this.item, this.onDelete});

  final MaintenanceItem item;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    Widget tile = GlassCard(
      radius: 20,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [
                Palette.warning.withValues(alpha: 0.3),
                Palette.violet.withValues(alpha: 0.2),
              ]),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.construction_rounded,
                color: Palette.warning, size: 21),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.type,
                  style: const TextStyle(
                    color: Palette.text,
                    fontSize: 14.5,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  '${item.vehicleLabel}',
                  style: const TextStyle(color: Palette.textDim, fontSize: 12.5),
                ),
                const SizedBox(height: 2),
                Text(
                  '${frDate(item.date)}${item.garage.isNotEmpty ? ' · ${item.garage}' : ''}',
                  style: const TextStyle(color: Palette.textMute, fontSize: 11.5),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                money(item.cout),
                style: const TextStyle(
                  color: Palette.warning,
                  fontSize: 14.5,
                  fontWeight: FontWeight.w800,
                ),
              ),
              if (onDelete != null)
                IconButton(
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline_rounded,
                      color: Palette.textMute, size: 20),
                ),
            ],
          ),
        ],
      ),
    );
    return tile;
  }
}