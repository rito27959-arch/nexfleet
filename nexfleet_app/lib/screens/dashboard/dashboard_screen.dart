import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../core/app_scope.dart';
import '../../core/models.dart';
import '../../core/theme.dart';
import '../../utils/format.dart';
import '../../widgets/charts.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/fx.dart';
import '../../widgets/glass.dart';
import '../../widgets/pressable.dart';
import '../drivers/drivers_screen.dart';
import '../vehicles/vehicles_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Stats? _stats;
  VidangeStats? _vgStats;
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
        app.api.get('/api/stats'),
        app.api.get('/api/vidanges/stats'),
      ]);
      if (!mounted) return;
      setState(() {
        _stats = Stats.fromJson(results[0]);
        _vgStats = VidangeStats.fromJson(results[1]);
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
        _error = 'Impossible de joindre le serveur.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      color: Palette.cyan,
      backgroundColor: const Color(0xFF0B1120),
      onRefresh: _load,
      child: _loading
          ? const SingleChildScrollView(
              physics: AlwaysScrollableScrollPhysics(),
              child: ScreenSkeleton(),
            )
          : _error != null
              ? SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: EmptyState(
                    icon: Icons.cloud_off_rounded,
                    title: _error!,
                    action: GradientButton(
                      label: 'Réessayer',
                      icon: Icons.refresh_rounded,
                      onPressed: _load,
                      expand: false,
                    ),
                  ),
                )
              : _Content(stats: _stats!, vgStats: _vgStats!),
    );
  }
}

class _Content extends StatelessWidget {
  const _Content({required this.stats, required this.vgStats});

  final Stats stats;
  final VidangeStats vgStats;

  @override
  Widget build(BuildContext context) {
    final user = app.session.username ?? '';
    final firstName = user.split(' ').first;
    final now = DateTime.now();

    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 90),
      children: [
        SpringShow(
          child: _Header(
            greeting: 'Bonjour, $firstName',
            date: _dateFr(now),
            dangerCount: stats.dangerCount,
          ),
        ),
        const SizedBox(height: 18),
        SpringShow(delay: const Duration(milliseconds: 60), child: _KpiGrid(stats: stats)),
        const SizedBox(height: 20),
        SpringShow(
          delay: const Duration(milliseconds: 120),
          child: _AlertsSection(alerts: stats.alerts),
        ),
        const SizedBox(height: 20),
        SpringShow(
          delay: const Duration(milliseconds: 180),
          child: _ExpenseDonut(
            maintenance: stats.maintenanceTotal,
            vidanges: stats.vidangesTotal,
          ),
        ),
        const SizedBox(height: 20),
        SpringShow(
          delay: const Duration(milliseconds: 240),
          child: _ControlsBars(controlsByMonth: stats.controlsByMonth),
        ),
        const SizedBox(height: 20),
        SpringShow(
          delay: const Duration(milliseconds: 300),
          child: _ForecastSection(forecast: vgStats.dueFirst),
        ),
      ],
    );
  }

  String _dateFr(DateTime d) {
    const days = [
      'lundi', 'mardi', 'mercredi', 'jeudi',
      'vendredi', 'samedi', 'dimanche',
    ];
    const months = [
      'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
      'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
    ];
    return '${days[d.weekday - 1]} ${d.day} ${months[d.month - 1]} ${d.year}';
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.greeting,
    required this.date,
    required this.dangerCount,
  });

  final String greeting;
  final String date;
  final int dangerCount;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                greeting,
                style: const TextStyle(
                  color: Palette.text,
                  fontSize: 23,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                date,
                style: const TextStyle(color: Palette.textDim, fontSize: 13),
              ),
            ],
          ),
        ),
        Row(
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: Palette.accent,
              ),
              alignment: Alignment.center,
              child: Text(
                (app.session.username ?? '?').characters.first.toUpperCase(),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 12),
            _Bell(dangerCount: dangerCount),
          ],
        ),
      ],
    );
  }
}

class _Bell extends StatelessWidget {
  const _Bell({required this.dangerCount});

  final int dangerCount;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 42,
      height: 42,
      child: Stack(
        clipBehavior: Clip.none,
        alignment: Alignment.center,
        children: [
          GlassCard(
            radius: 14,
            padding: EdgeInsets.zero,
            child: const Icon(
              Icons.notifications_none_rounded,
              color: Palette.textDim,
              size: 21,
            ),
          ),
          if (dangerCount > 0)
            Positioned(
              top: -4,
              right: -4,
              child: Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: Palette.danger,
                  shape: BoxShape.circle,
                  border: Border.all(color: Palette.bg, width: 2),
                ),
                child: Text(
                  '$dangerCount',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 8.5,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _KpiGrid extends StatelessWidget {
  const _KpiGrid({required this.stats});

  final Stats stats;

  @override
  Widget build(BuildContext context) {
    final tiles = [
      _Kpi(
        label: 'En service',
        value: stats.enService.toDouble(),
        color: Palette.success,
        icon: Icons.check_circle_rounded,
      ),
      _Kpi(
        label: 'Maintenance',
        value: stats.enMaintenance.toDouble(),
        color: Palette.warning,
        icon: Icons.construction_rounded,
      ),
      _Kpi(
        label: 'En panne',
        value: stats.enPanne.toDouble(),
        color: Palette.danger,
        icon: Icons.priority_high_rounded,
      ),
      _Kpi(
        label: 'Conducteurs',
        value: stats.drivers.toDouble(),
        color: Palette.violet,
        icon: Icons.badge_rounded,
      ),
    ];

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.55,
      children: [
        for (final t in tiles)
          ScaleTap(
            onTap: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => const VehiclesScreen(),
            )),
            child: GlassCard(
              padding: const EdgeInsets.all(15),
              glow: t.color.withValues(alpha: 0.25),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: t.color.withValues(alpha: 0.14),
                    ),
                    child: Icon(t.icon, color: t.color, size: 17),
                  ),
                  const SizedBox(height: 10),
                  AnimatedNumber(
                    t.value,
                    style: TextStyle(
                      color: Palette.text,
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    t.label,
                    style: const TextStyle(
                      color: Palette.textDim,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _Kpi {
  const _Kpi({
    required this.label,
    required this.value,
    required this.color,
    required this.icon,
  });

  final String label;
  final double value;
  final Color color;
  final IconData icon;
}

class _AlertsSection extends StatelessWidget {
  const _AlertsSection({required this.alerts});

  final List<Alert> alerts;

  @override
  Widget build(BuildContext context) {
    final top = alerts.take(4).toList();
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'Échéances à surveiller',
                style: TextStyle(
                  color: Palette.text,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              if (alerts.isNotEmpty)
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: Container(
                    key: ValueKey(alerts.length),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 9, vertical: 3),
                    decoration: BoxDecoration(
                      color: alerts.any((a) => a.isDanger)
                          ? Palette.danger.withValues(alpha: 0.18)
                          : Palette.warning.withValues(alpha: 0.16),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      '${alerts.length}',
                      style: TextStyle(
                        color: alerts.any((a) => a.isDanger)
                            ? Palette.danger
                            : Palette.warning,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),
          if (top.isEmpty)
            const Row(
              children: [
                Icon(Icons.verified_rounded,
                    color: Palette.success, size: 18),
                SizedBox(width: 8),
                Text(
                  'Aucune échéance critique — tout est à jour',
                  style: TextStyle(color: Palette.textDim, fontSize: 13),
                ),
              ],
            )
          else
            Staggered(
              itemCount: top.length,
              itemBuilder: (context, i) => _AlertTile(alert: top[i]),
            ),
        ],
      ),
    );
  }
}

class _AlertTile extends StatelessWidget {
  const _AlertTile({required this.alert});

  final Alert alert;

  @override
  Widget build(BuildContext context) {
    final color = Palette.level(alert.level);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: color.withValues(alpha: 0.07),
          border: Border.all(color: color.withValues(alpha: 0.35)),
        ),
        child: Row(
          children: [
            Icon(
              alert.isDanger ? Icons.error_rounded : Icons.schedule_rounded,
              color: color,
              size: 19,
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${alert.label} · ${alert.vehicle}',
                    style: const TextStyle(
                      color: Palette.text,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    alert.msg,
                    style: const TextStyle(
                        color: Palette.textDim, fontSize: 12.5),
                  ),
                ],
              ),
            ),
            Text(
              alert.isDanger ? '' : '${alert.days}j',
              style: TextStyle(
                color: color,
                fontSize: 13,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ExpenseDonut extends StatelessWidget {
  const _ExpenseDonut({required this.maintenance, required this.vidanges});

  final double maintenance;
  final double vidanges;

  @override
  Widget build(BuildContext context) {
    final total = maintenance + vidanges;
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          Donut(
            size: 118,
            thickness: 13,
            segments: [
              (value: maintenance, color: Palette.cyan),
              (value: vidanges, color: Palette.violet),
            ],
            center: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'ENTRETIEN',
                  style: TextStyle(
                    color: Palette.textMute,
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  inr(total),
                  style: const TextStyle(
                    color: Palette.text,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 22),
          Expanded(
            child: Column(
              children: [
                _Legend(
                  color: Palette.cyan,
                  label: 'Maintenance',
                  value: maintenance,
                ),
                const SizedBox(height: 10),
                _Legend(
                  color: Palette.violet,
                  label: 'Vidanges',
                  value: vidanges,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({
    required this.color,
    required this.label,
    required this.value,
  });

  final Color color;
  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 9),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(color: Palette.textDim, fontSize: 13),
          ),
        ),
        AnimatedNumber(
          value,
          style: const TextStyle(
            color: Palette.text,
            fontSize: 13.5,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _ControlsBars extends StatelessWidget {
  const _ControlsBars({required this.controlsByMonth});

  final List<({String month, int count})> controlsByMonth;

  @override
  Widget build(BuildContext context) {
    final values =
        controlsByMonth.map((m) => m.count.toDouble()).toList(growable: false);
    final labels =
        controlsByMonth.map((m) => frMonth(m.month)).toList(growable: false);
    final total = controlsByMonth.fold<int>(0, (a, m) => a + m.count);

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'Contrôles',
                style: TextStyle(
                  color: Palette.text,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              Text(
                '$total sur 6 mois',
                style: const TextStyle(color: Palette.textMute, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Bars(values: values, labels: labels),
        ],
      ),
    );
  }
}

class _ForecastSection extends StatelessWidget {
  const _ForecastSection({required this.forecast});

  final List<VidangeForecast> forecast;

  @override
  Widget build(BuildContext context) {
    final due = forecast.where((f) => f.due).take(3).toList();
    final next = forecast.where((f) => !f.due).take(2).toList();
    final items = [...due, ...next];

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Vidanges à prévoir',
            style: TextStyle(
              color: Palette.text,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 14),
          if (items.isEmpty)
            const Text(
              'Aucune prévision — ajoutez des vidanges.',
              style: TextStyle(color: Palette.textDim, fontSize: 13),
            )
          else
            Column(
              children: [
                for (final f in items) ...[
                  _ForecastTile(forecast: f),
                  const SizedBox(height: 8),
                ],
              ],
            ),
        ],
      ),
    );
  }
}

class _ForecastTile extends StatelessWidget {
  const _ForecastTile({required this.forecast});

  final VidangeForecast forecast;

  @override
  Widget build(BuildContext context) {
    final color = forecast.due ? Palette.danger : Palette.success;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
      ),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color.withValues(alpha: 0.14),
            ),
            child: Icon(
              forecast.due ? Icons.oil_barrel_rounded : Icons.hourglass_top,
              color: color,
              size: 19,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${forecast.marque} ${forecast.modele}'.trim().isNotEmpty
                      ? '${forecast.marque} ${forecast.modele}'.trim()
                      : forecast.label,
                  style: const TextStyle(
                    color: Palette.text,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 5),
                Gauge(
                  frac: forecast.due
                      ? 0
                      : (() {
                          final f = 1 -
                              forecast.kmLeft /
                                  (forecast.kmDue > 0 ? forecast.kmDue : 1);
                          return f < 0 ? 0.0 : (f > 1 ? 1.0 : f);
                        })(),
                  color: color,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            forecast.due
                ? 'À faire'
                : '${inr(forecast.kmLeft)} km',
            style: TextStyle(
              color: color,
              fontSize: 12.5,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}