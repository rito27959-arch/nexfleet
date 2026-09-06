import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api_client.dart';
import '../../core/app_scope.dart';
import '../../core/models.dart';
import '../../core/theme.dart';
import '../../utils/format.dart';
import '../../widgets/glass.dart';
import '../../widgets/toast.dart';

/// Feuille d'ajout / édition d'une vidange (miroir du formulaire Web).
class VidangeFormSheet extends StatefulWidget {
  const VidangeFormSheet({super.key, this.vidange, this.vehicleId, this.immatriculation});

  final Vidange? vidange;
  final int? vehicleId;
  final String? immatriculation;

  @override
  State<VidangeFormSheet> createState() => _VidangeFormSheetState();
}

class _VidangeFormSheetState extends State<VidangeFormSheet> {
  final _formKey = GlobalKey<FormState>();
  final _date = TextEditingController();
  final _km = TextEditingController();
  final _interval = TextEditingController();
  final _huile = TextEditingController();
  final _quantite = TextEditingController();
  final _cout = TextEditingController();
  final _garage = TextEditingController();
  final _notes = TextEditingController();

  late int? _vehicleId = widget.vidange?.vehicleId ?? widget.vehicleId;
  late bool _fH = widget.vidange?.filtreHuile ?? false;
  late bool _fG = widget.vidange?.filtreGasoil ?? false;
  late bool _hT = widget.vidange?.huileTransmission ?? false;
  late bool _lR = widget.vidange?.liquideRefroidissement ?? false;
  late bool _lL = widget.vidange?.liquideLaveglace ?? false;

  List<Vehicle> _vehicles = [];
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _date.text = todayIso();
    _km.text = widget.vidange?.km.toString() ?? '';
    _interval.text = (widget.vidange?.kmInterval ?? 10000).toString();
    _huile.text = widget.vidange?.huile ?? '';
    _quantite.text = widget.vidange?.quantite?.toString() ?? '';
    _cout.text = widget.vidange?.cout.toString() ?? '';
    _garage.text = widget.vidange?.garage ?? '';
    _notes.text = widget.vidange?.notes ?? '';
    _loadVehicles();
  }

  Future<void> _loadVehicles() async {
    try {
      final r = await app.api.get('/api/vehicles');
      if (!mounted) return;
      setState(() {
        _vehicles = [
          for (final v in (r['vehicles'] as List? ?? const []))
            if (v is Map<String, dynamic>) Vehicle.fromJson(v)
        ];
        if (_vehicleId == null && _vehicles.isNotEmpty) {
          _vehicleId = _vehicles.first.id;
        }
      });
    } catch (_) {}
  }

  @override
  void dispose() {
    _date.dispose();
    _km.dispose();
    _interval.dispose();
    _huile.dispose();
    _quantite.dispose();
    _cout.dispose();
    _garage.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    if (_vehicleId == null) {
      showNexToast(context, 'Choisissez un véhicule', kind: Nest.error);
      return;
    }
    HapticFeedback.mediumImpact();
    setState(() => _saving = true);
    try {
      final body = <String, dynamic>{
        'vehicle_id': _vehicleId,
        'date': _date.text.trim(),
        'km': int.tryParse(_km.text.trim()) ?? 0,
        'km_interval': int.tryParse(_interval.text.trim()) ?? 0,
        'huile': _huile.text.trim(),
        'quantite': double.tryParse(_quantite.text.trim()) ?? 0,
        'filtre_huile': _fH,
        'filtre_gasoil': _fG,
        'huile_transmission': _hT,
        'liquide_refroidissement': _lR,
        'liquide_laveglace': _lL,
        'cout': double.tryParse(_cout.text.trim()) ?? 0,
        'garage': _garage.text.trim(),
        'notes': _notes.text.trim(),
      };
      if (widget.vidange == null) {
        await app.api.post('/api/vidanges', body);
      } else {
        await app.api.put('/api/vidanges/${widget.vidange!.id}', body);
      }
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      showNexToast(context, e.message, kind: Nest.error);
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
      showNexToast(context, 'Impossible de joindre le serveur',
          kind: Nest.error);
    }
  }

  @override
  Widget build(BuildContext context) {
    final prochaineAuto = int.tryParse(_km.text.trim()) == null
        ? 0
        : (int.tryParse(_km.text.trim()) ?? 0) +
            (int.tryParse(_interval.text.trim()) ?? 0);

    return AnimatedPadding(
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOut,
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF12182B), Color(0xFF080B16)],
          ),
          borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
        ),
        child: DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.93,
          maxChildSize: 0.97,
          minChildSize: 0.5,
          builder: (context, scrollController) => SingleChildScrollView(
            controller: scrollController,
            padding: const EdgeInsets.fromLTRB(22, 16, 22, 34),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 44,
                    height: 5,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                Text(
                  widget.vidange == null
                      ? 'Nouvelle vidange'
                      : 'Modifier la vidange #${widget.vidange!.id}',
                  style: const TextStyle(
                    color: Palette.text,
                    fontSize: 21,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 22),
                Form(
                  key: _formKey,
                  child: Column(
                    children: [
                      _VehiclePicker(
                        vehicles: _vehicles,
                        selectedId: _vehicleId,
                        lockedLabel: widget.immatriculation,
                        onChanged: (id) =>
                            setState(() => _vehicleId = id),
                      ),
                      const SizedBox(height: 13),
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _date,
                              readOnly: true,
                              onTap: () => _pickDate(context),
                              decoration: const InputDecoration(
                                labelText: 'Date',
                                prefixIcon: Icon(
                                    Icons.event_outlined,
                                    size: 19),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextFormField(
                              controller: _km,
                              keyboardType: TextInputType.number,
                              validator: (v) =>
                                  (v == null || v.trim().isEmpty)
                                      ? 'Km requis'
                                      : null,
                              onChanged: (_) => setState(() {}),
                              decoration: const InputDecoration(
                                labelText: 'Km compteur',
                                prefixIcon: Icon(
                                    Icons.speed_rounded,
                                    size: 19),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 13),
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _interval,
                              keyboardType: TextInputType.number,
                              onChanged: (_) => setState(() {}),
                              decoration: const InputDecoration(
                                labelText: 'Intervalle (km)',
                                prefixIcon: Icon(
                                    Icons.repeat_rounded, size: 19),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextFormField(
                              controller: _huile,
                              decoration: const InputDecoration(
                                labelText: 'Huile',
                                prefixIcon: Icon(
                                    Icons.opacity_rounded, size: 19),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 13),
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _quantite,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                      decimal: true),
                              decoration: const InputDecoration(
                                labelText: 'Quantité (L)',
                                prefixIcon: Icon(
                                    Icons.water_drop_outlined,
                                    size: 19),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextFormField(
                              controller: _cout,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Coût (FCFA)',
                                prefixIcon: Icon(
                                    Icons.payments_outlined,
                                    size: 18),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 13),
                      TextFormField(
                        controller: _garage,
                        decoration: const InputDecoration(
                          labelText: 'Garage',
                          prefixIcon: Icon(Icons.garage_rounded, size: 19),
                        ),
                      ),
                      const SizedBox(height: 13),
                      TextFormField(
                        controller: _notes,
                        maxLines: 2,
                        decoration: const InputDecoration(
                          labelText: 'Observations (optionnel)',
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 18),
                      const _Labeled('Remplacements effectués'),
                      const SizedBox(height: 10),
                      _CheckGrid(
                        items: [
                          ('Huile moteur', _fH, (v) => _fH = v),
                          ('Filtre gasoil', _fG, (v) => _fG = v),
                          ('Huile transmission', _hT, (v) => _hT = v),
                          ('Liquide refroidissement', _lR, (v) => _lR = v),
                          ('Liquide lave-glace', _lL, (v) => _lL = v),
                        ],
                        onToggle: () => setState(() {}),
                      ),
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(13),
                        decoration: BoxDecoration(
                          color: Palette.cyan.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color:
                                Palette.cyan.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.flag_rounded,
                                color: Palette.cyan, size: 18),
                            const SizedBox(width: 10),
                            Text(
                              'Prochaine vidange : ',
                              style: TextStyle(
                                color: Palette.text.withValues(alpha: 0.8),
                                fontSize: 13,
                              ),
                            ),
                            Text(
                              '${inr(prochaineAuto)} km',
                              style: const TextStyle(
                                color: Palette.cyan,
                                fontSize: 14,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 22),
                      GradientButton(
                        label: widget.vidange == null
                            ? 'Ajouter la vidange'
                            : 'Enregistrer',
                        icon: Icons.check_rounded,
                        loading: _saving,
                        onPressed: _save,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _pickDate(BuildContext context) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime(now.year, now.month, now.day),
      firstDate: DateTime(2000),
      lastDate: DateTime(now.year + 5),
      builder: (context, child) => Theme(
        data: Theme.of(context).copyWith(
          colorScheme: Theme.of(context).colorScheme.copyWith(
                primary: Palette.cyan,
                onPrimary: Colors.black,
                surface: const Color(0xFF111830),
              ),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      setState(() {
        _date.text =
            '${picked.year.toString().padLeft(4, '0')}-'
            '${picked.month.toString().padLeft(2, '0')}-'
            '${picked.day.toString().padLeft(2, '0')}';
      });
    }
  }
}

class _Labeled extends StatelessWidget {
  const _Labeled(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(color: Palette.textDim, fontSize: 13.5),
    );
  }
}

class _VehiclePicker extends StatelessWidget {
  const _VehiclePicker({
    required this.vehicles,
    required this.selectedId,
    required this.lockedLabel,
    required this.onChanged,
  });

  final List<Vehicle> vehicles;
  final int? selectedId;
  final String? lockedLabel;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    if (lockedLabel != null && lockedLabel!.isNotEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Row(
          children: [
            const Icon(Icons.directions_car_rounded,
                color: Palette.textDim, size: 18),
            const SizedBox(width: 10),
            Text(
              lockedLabel!,
              style: const TextStyle(
                color: Palette.text,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: DropdownButtonFormField<int>(
        value: selectedId,
        isExpanded: true,
        dropdownColor: const Color(0xFF111830),
        decoration: const InputDecoration(
          labelText: 'Véhicule',
          border: InputBorder.none,
        ),
        items: [
          for (final v in vehicles)
            DropdownMenuItem(
              value: v.id,
              child: Text(
                '${v.immatriculation} · ${v.label}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
        ],
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
        validator: (v) => v == null ? 'Véhicule requis' : null,
      ),
    );
  }
}

/// Grille de cases à cocher animées (remplacements).
class _CheckGrid extends StatelessWidget {
  const _CheckGrid({required this.items, required this.onToggle});

  final List<(String, bool, ValueChanged<bool>)> items;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final (label, value, setter) in items)
          _CheckPill(
            label: label,
            value: value,
            onChanged: (v) {
              setter(v);
              HapticFeedback.selectionClick();
              onToggle();
            },
          ),
      ],
    );
  }
}

class _CheckPill extends StatelessWidget {
  const _CheckPill({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => onChanged(!value),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Motion.springOut,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          gradient: value
              ? LinearGradient(colors: [
                  Palette.success.withValues(alpha: 0.26),
                  Palette.cyan.withValues(alpha: 0.12),
                ])
              : null,
          color: value ? null : Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: value
                ? Palette.success.withValues(alpha: 0.7)
                : Colors.white.withValues(alpha: 0.09),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 18,
              height: 18,
              decoration: BoxDecoration(
                color: value ? Palette.success : Colors.transparent,
                shape: BoxShape.circle,
                border: Border.all(
                  color: value
                      ? Colors.transparent
                      : Colors.white.withValues(alpha: 0.3),
                ),
              ),
              child: value
                  ? const Icon(Icons.check_rounded,
                      color: Colors.white, size: 13)
                  : null,
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: value ? Palette.text : Palette.textDim,
                fontSize: 12.5,
                fontWeight: value ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}