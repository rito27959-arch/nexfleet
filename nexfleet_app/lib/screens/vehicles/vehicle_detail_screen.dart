import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api_client.dart';
import '../../core/app_scope.dart';
import '../../core/models.dart';
import '../../core/theme.dart';
import '../../utils/format.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/fx.dart';
import '../../widgets/glass.dart';
import '../../widgets/pressable.dart';
import '../../widgets/toast.dart';
import '../vidanges/vidange_form_sheet.dart';
import 'vehicle_form_sheet.dart';

class VehicleDetailScreen extends StatefulWidget {
  const VehicleDetailScreen({super.key, required this.vehicleId});

  final int vehicleId;

  @override
  State<VehicleDetailScreen> createState() => _VehicleDetailScreenState();
}

class _VehicleDetailScreenState extends State<VehicleDetailScreen> {
  VehicleDetail? _detail;
  bool _loading = true;
  String? _error;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r =
          await app.api.get('/api/vehicles/${widget.vehicleId}/detail');
      if (!mounted) return;
      setState(() {
        _detail = VehicleDetail.fromJson(r);
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

  Future<void> _edit() async {
    final v = _detail!.vehicle;
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => VehicleFormSheet(vehicle: v),
    );
    if (ok == true) {
      showNexToast(context, 'Véhicule mis à jour', kind: Nest.success);
      _load();
    }
  }

  Future<void> _addVidange() async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => VidangeFormSheet(
        vehicleId: widget.vehicleId,
        immatriculation: _detail!.vehicle.immatriculation,
      ),
    );
    if (ok == true) {
      showNexToast(context, 'Vidange enregistrée', kind: Nest.success);
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(child: ScreenSkeleton()),
      );
    }
    if (_error != null) {
      return Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: EmptyState(
            icon: Icons.cloud_off_rounded,
            title: _error!,
            action: GradientButton(
              label: 'Réessayer',
              onPressed: _load,
              expand: false,
            ),
          ),
        ),
      );
    }
    final v = _detail!.vehicle;
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverAppBar(
              backgroundColor: Colors.transparent,
              pinned: true,
              stretch: true,
              expandedHeight: 210,
              leading: _BackFab(),
              actions: [
                IconButton(
                  onPressed: _edit,
                  tooltip: 'Modifier',
                  icon: const Icon(Icons.edit_rounded,
                      color: Palette.textDim),
                ),
              ],
              flexibleSpace: FlexibleSpaceBar(
                background: Hero(
                  tag: 'vh-${widget.vehicleId}',
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          Palette.cyan.withValues(alpha: 0.45),
                          Palette.violet.withValues(alpha: 0.25),
                          Palette.bg,
                        ],
                      ),
                    ),
                    child: Stack(
                      children: [
                        Center(
                          child: Icon(
                            Icons.local_shipping_rounded,
                            color: Colors.white.withValues(alpha: 0.7),
                            size: 84,
                          ),
                        ),
                        Positioned(
                          left: 18,
                          right: 18,
                          bottom: 8,
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      v.immatriculation,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 22,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: 1,
                                      ),
                                    ),
                                    Text(
                                      v.label,
                                      style: TextStyle(
                                        color: Colors.white
                                            .withValues(alpha: 0.85),
                                        fontSize: 14,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(18, 14, 18, 90),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Staggered(
                      itemCount: 1,
                      itemBuilder: (_, __) =>
                          _InfoGrid(vehicle: v, total: _detail!.totalSpent),
                    ),
                    const SizedBox(height: 20),
                    _AlertsStrip(alerts: v.alerts),
                    const SizedBox(height: 20),
                    _Tabs(selected: _tab, onChanged: (t) {
                      HapticFeedback.selectionClick();
                      setState(() => _tab = t);
                    }),
                    const SizedBox(height: 14),
                    _TabBody(
                      tab: _tab,
                      detail: _detail!,
                      onAddVidange: _addVidange,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        heroTag: 'fabs',
        backgroundColor: Palette.cyan,
        foregroundColor: Palette.bg,
        onPressed: _addVidange,
        icon: const Icon(Icons.oil_barrel_rounded),
        label: const Text('Vidange'),
      ),
    );
  }
}

class _BackFab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8),
      child: ScaleTap(
        haptic: true,
        onTap: () => Navigator.of(context).pop(),
        child: Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            color: const Color(0xCC05070F),
            borderRadius: BorderRadius.circular(13),
            border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
          ),
          child: const Icon(Icons.arrow_back_rounded,
              color: Palette.text, size: 20),
        ),
      ),
    );
  }
}

class _InfoGrid extends StatelessWidget {
  const _InfoGrid({required this.vehicle, required this.total});

  final Vehicle vehicle;
  final double total;

  @override
  Widget build(BuildContext context) {
    final items = [
      (Icons.speed_rounded, 'Kilométrage', '${inr(vehicle.kilometrage)} km'),
      (Icons.local_gas_station_rounded, 'Carburant', vehicle.carburant),
      (Icons.calendar_today_outlined, 'Année', '${vehicle.annee ?? '—'}'),
      (Icons.bolt_rounded, 'CV', '${vehicle.cv ?? '—'}'),
      (Icons.account_balance_outlined, 'Direction',
          vehicle.direction ?? '—'),
      (Icons.location_on_outlined, 'Affectation', vehicle.affectation ?? '—'),
      (Icons.payments_outlined, 'Dépenses', money(total)),
      (Icons.category_outlined, 'Type', vehicle.type),
    ];
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        childAspectRatio: 2.6,
        mainAxisSpacing: 10,
        crossAxisSpacing: 12,
        children: [
          for (final (icon, label, value) in items)
            Row(
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: Palette.cyan.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: Icon(icon, color: Palette.cyan, size: 17),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        label,
                        style: const TextStyle(
                            color: Palette.textMute, fontSize: 10.5),
                      ),
                      Text(
                        value,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Palette.text,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }
}

class _AlertsStrip extends StatelessWidget {
  const _AlertsStrip({required this.alerts});

  final List<Alert> alerts;

  @override
  Widget build(BuildContext context) {
    if (alerts.isEmpty) return const SizedBox.shrink();
    return GlassCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Échéances',
            style: TextStyle(
              color: Palette.text,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          for (final a in alerts) ...[
            Row(
              children: [
                Icon(
                  a.isDanger ? Icons.error_rounded : Icons.schedule_rounded,
                  color: Palette.level(a.level),
                  size: 16,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    a.msg,
                    style: const TextStyle(
                        color: Palette.textDim, fontSize: 12.5),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
          ],
        ],
      ),
    );
  }
}

class _Tabs extends StatelessWidget {
  const _Tabs({required this.selected, required this.onChanged});

  final int selected;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    const labels = ['Maintenance', 'Vidanges'];
    return Container(
      height: 46,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          for (var i = 0; i < labels.length; i++)
            Expanded(
              child: GestureDetector(
                onTap: () => onChanged(i),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 260),
                  curve: Motion.springOut,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    gradient: selected == i ? Palette.accent : null,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    labels[i],
                    style: TextStyle(
                      color: selected == i ? Colors.white : Palette.textDim,
                      fontSize: 13,
                      fontWeight:
                          selected == i ? FontWeight.w800 : FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _TabBody extends StatelessWidget {
  const _TabBody({
    required this.tab,
    required this.detail,
    required this.onAddVidange,
  });

  final int tab;
  final VehicleDetail detail;
  final VoidCallback onAddVidange;

  @override
  Widget build(BuildContext context) {
    if (tab == 0) {
      final items = detail.maintenance;
      if (items.isEmpty) {
        return EmptyState(
          icon: Icons.build_rounded,
          title: 'Aucune maintenance',
          subtitle: 'Enregistrez votre première intervention.',
        );
      }
      return Staggered(
        itemCount: items.length,
        itemBuilder: (context, i) => Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: GlassCard(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: Palette.warning.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: const Icon(Icons.construction_rounded,
                      color: Palette.warning, size: 19),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        items[i].type,
                        style: const TextStyle(
                          color: Palette.text,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${frDate(items[i].date)}${items[i].garage.isNotEmpty ? ' · ${items[i].garage}' : ''}',
                        style: const TextStyle(
                            color: Palette.textDim, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                Text(
                  money(items[i].cout),
                  style: const TextStyle(
                    color: Palette.warning,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    // Vidanges
    final vg = detail.vidanges;
    if (vg.isEmpty) {
      return EmptyState(
        icon: Icons.oil_barrel_rounded,
        title: 'Aucune vidange',
        subtitle: 'Le bouton « Vidange » permet d’en ajouter.',
        action: GradientButton(
          label: 'Ajouter une vidange',
          onPressed: onAddVidange,
          expand: false,
        ),
      );
    }
    return Staggered(
      itemCount: vg.length,
      itemBuilder: (context, i) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: GlassCard(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: Palette.violet.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: const Icon(Icons.oil_barrel_rounded,
                    color: Palette.violet, size: 19),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      frDate(vg[i].date),
                      style: const TextStyle(
                        color: Palette.text,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${inr(vg[i].km)} km${vg[i].huile.isNotEmpty ? ' · ${vg[i].huile}' : ''}',
                      style: const TextStyle(
                          color: Palette.textDim, fontSize: 12),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '→ ${inr(vg[i].prochaineKm)} km',
                    style: const TextStyle(
                      color: Palette.cyan,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    money(vg[i].cout),
                    style: const TextStyle(
                        color: Palette.textMute, fontSize: 11.5),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}