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
import 'vehicle_detail_screen.dart';
import 'vehicle_form_sheet.dart';

class VehiclesScreen extends StatefulWidget {
  const VehiclesScreen({super.key});

  @override
  State<VehiclesScreen> createState() => _VehiclesScreenState();
}

class _VehiclesScreenState extends State<VehiclesScreen> {
  final _search = TextEditingController();
  List<Vehicle> _vehicles = [];
  bool _loading = true;
  String? _error;
  String _statut = '';

  static const _statuts = ['', 'En service', 'En maintenance', 'En panne', 'Garé'];

  @override
  void initState() {
    super.initState();
    _search.addListener(_onSearch);
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _onSearch() {
    _load();
  }

  Future<void> _load() async {
    try {
      final q = <String, String>{};
      if (_search.text.trim().isNotEmpty) q['search'] = _search.text.trim();
      if (_statut.isNotEmpty) q['statut'] = _statut;
      final r = await app.api.get('/api/vehicles', q.isEmpty ? null : q);
      if (!mounted) return;
      setState(() {
        _vehicles = [
          for (final v in (r['vehicles'] as List? ?? const []))
            if (v is Map<String, dynamic>) Vehicle.fromJson(v)
        ];
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

  Future<void> _addVehicle() async {
    final created = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const VehicleFormSheet(),
    );
    if (created == true) {
      showNexToast(context, 'Véhicule ajouté', kind: Nest.success);
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _Header(
          count: _vehicles.length,
          search: _search,
          onAdd: _addVehicle,
        ),
        FilterChipsRow(
          selected: _statut,
          statuses: _statuts,
          onChanged: (s) {
            setState(() => _statut = s);
            _load();
          },
        ),
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
                  : _vehicles.isEmpty
                      ? const EmptyState(
                          icon: Icons.directions_car_rounded,
                          title: 'Aucun véhicule',
                          subtitle: 'Ajoutez votre premier véhicule.',
                        )
                      : RefreshIndicator(
                          color: Palette.cyan,
                          backgroundColor: const Color(0xFF0B1120),
                          onRefresh: _load,
                          child: GridView.builder(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.fromLTRB(18, 6, 18, 100),
                            gridDelegate:
                                const SliverGridDelegateWithMaxCrossAxisExtent(
                              maxCrossAxisExtent: 360,
                              mainAxisSpacing: 14,
                              crossAxisSpacing: 14,
                              childAspectRatio: 1.25,
                            ),
                            itemCount: _vehicles.length,
                            itemBuilder: (context, i) =>
                                _VehicleCard(vehicle: _vehicles[i]),
                          ),
                        ),
        ),
      ],
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.count,
    required this.search,
    required this.onAdd,
  });

  final int count;
  final TextEditingController search;
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Véhicules',
                  style: TextStyle(
                    color: Palette.text,
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 250),
                child: Text(
                  '$count',
                  key: ValueKey(count),
                  style: const TextStyle(
                      color: Palette.textMute, fontSize: 13.5),
                ),
              ),
              const SizedBox(width: 6),
              ScaleTap(
                haptic: false,
                onTap: () {
                  pulseMedium();
                  onAdd();
                },
                child: Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    gradient: Palette.accent,
                    borderRadius: BorderRadius.circular(13),
                    boxShadow: [
                      BoxShadow(
                        color: Palette.indigo.withValues(alpha: 0.4),
                        blurRadius: 14,
                      ),
                    ],
                  ),
                  child: const Icon(Icons.add_rounded,
                      color: Colors.white, size: 22),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: search,
            decoration: const InputDecoration(
              hintText: 'Rechercher une immatriculation, marque…',
              prefixIcon: Icon(Icons.search_rounded, size: 20),
              isDense: true,
            ),
          ),
        ],
      ),
    );
  }
}

/// Chips de filtres par statut (défilement horizontal).
class FilterChipsRow extends StatelessWidget {
  const FilterChipsRow({
    super.key,
    required this.selected,
    required this.statuses,
    required this.onChanged,
  });

  final String selected;
  final List<String> statuses;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 6),
        children: [
          for (final s in statuses)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilterChipNex(
                label: s.isEmpty ? 'Tous' : s,
                selected: selected == s,
                onTap: () => onChanged(s),
              ),
            ),
        ],
      ),
    );
  }
}

class _VehicleCard extends StatelessWidget {
  const _VehicleCard({required this.vehicle});

  final Vehicle vehicle;

  @override
  Widget build(BuildContext context) {
    final danger = vehicle.dangerousAlerts;
    return ScaleTap(
      scale: 0.965,
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => VehicleDetailScreen(vehicleId: vehicle.id),
      )),
      child: GlassCard(
        padding: EdgeInsets.zero,
        radius: 22,
        glow: danger.isNotEmpty ? Palette.danger : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Hero(
                tag: 'vh-${vehicle.id}',
                child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      _hue(vehicle.id).withValues(alpha: 0.55),
                      _hue(vehicle.id + 3).withValues(alpha: 0.18),
                    ],
                  ),
                ),
                child: Stack(
                  children: [
                    Center(
                      child: Icon(
                        Icons.local_shipping_rounded,
                        color: Colors.white.withValues(alpha: 0.75),
                        size: 46,
                      ),
                    ),
                    Positioned(
                      top: 10,
                      left: 10,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 9, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xCC05070F),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: Colors.white.withValues(alpha: 0.14),
                          ),
                        ),
                        child: Text(
                          vehicle.immatriculation,
                          style: const TextStyle(
                            color: Palette.text,
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.6,
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      top: 10,
                      right: 10,
                      child: _StatusDot(status: vehicle.statut ?? ''),
                    ),
                  ],
                ),
              ),
            ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    vehicle.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Palette.text,
                      fontSize: 14.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Row(
                    children: [
                      const Icon(Icons.speed_rounded,
                          color: Palette.textMute, size: 13),
                      const SizedBox(width: 4),
                      Text(
                        '${inr(vehicle.kilometrage)} km',
                        style: const TextStyle(
                            color: Palette.textDim, fontSize: 12),
                      ),
                      const Spacer(),
                      if (danger.isNotEmpty)
                        Icon(Icons.warning_amber_rounded,
                            color: Palette.danger, size: 15)
                      else
                        Icon(Icons.check_circle_rounded,
                            color: Palette.success.withValues(alpha: 0.7),
                            size: 15),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static Color _hue(int seed) {
    const cols = [
      Color(0xFF22D3EE),
      Color(0xFF38BDF8),
      Color(0xFF818CF8),
      Color(0xFFC084FC),
      Color(0xFF2DD4BF),
    ];
    return cols[seed % cols.length];
  }
}

class _StatusDot extends StatelessWidget {
  const _StatusDot({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final color = status.contains('Maintenance')
        ? Palette.warning
        : status.contains('Panne')
            ? Palette.danger
            : status.contains('Garé')
                ? Palette.textMute
                : Palette.success;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: const Color(0xD9050710),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 5),
          Text(
            status,
            style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}