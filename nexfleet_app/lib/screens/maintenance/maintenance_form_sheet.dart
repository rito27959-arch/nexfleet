import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api_client.dart';
import '../../core/app_scope.dart';
import '../../core/models.dart';
import '../../core/theme.dart';
import '../../utils/format.dart';
import '../../widgets/glass.dart';
import '../../widgets/toast.dart';

class MaintenanceFormSheet extends StatefulWidget {
  const MaintenanceFormSheet({super.key});

  @override
  State<MaintenanceFormSheet> createState() => _MaintenanceFormSheetState();
}

class _MaintenanceFormSheetState extends State<MaintenanceFormSheet> {
  final _formKey = GlobalKey<FormState>();
  final _type = TextEditingController(text: 'Révision');
  final _date = TextEditingController(text: todayIso());
  final _cout = TextEditingController();
  final _garage = TextEditingController();
  final _notes = TextEditingController();

  static const _types = [
    'Révision',
    'Freinage',
    'Pneumatique',
    'Moteur',
    'Électricité',
    'Carrosserie',
    'Autre',
  ];

  List<Vehicle> _vehicles = [];
  int? _vehicleId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
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

  String? _typeErr(String? v) => (v == null || v.trim().isEmpty)
      ? 'Type requis'
      : null;

  @override
  void dispose() {
    _type.dispose();
    _date.dispose();
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
      await app.api.post('/api/maintenance', {
        'vehicle_id': _vehicleId,
        'type': _type.text.trim(),
        'date': _date.text.trim(),
        'cout': double.tryParse(_cout.text.trim()) ?? 0,
        'garage': _garage.text.trim(),
        'notes': _notes.text.trim(),
      });
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
        child: SingleChildScrollView(
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
              const Text(
                'Nouvelle intervention',
                style: TextStyle(
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
                      onChanged: (id) => setState(() => _vehicleId = id),
                    ),
                    const SizedBox(height: 13),
                    SizedBox(
                      height: 46,
                      child: ListView(
                        scrollDirection: Axis.horizontal,
                        children: [
                          for (final t in _types)
                            Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: FilterChipNex(
                                label: t,
                                selected: _type.text == t,
                                onTap: () =>
                                    setState(() => _type.text = t),
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    TextFormField(
                      controller: _type,
                      validator: _typeErr,
                      decoration: const InputDecoration(
                        labelText: 'Type',
                        prefixIcon:
                            Icon(Icons.build_rounded, size: 19),
                      ),
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
                              prefixIcon: Icon(Icons.event_outlined,
                                  size: 19),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _cout,
                            keyboardType: TextInputType.number,
                            validator: (v) => (v == null || v.trim().isEmpty)
                                ? 'Coût requis'
                                : null,
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
                    const SizedBox(height: 24),
                    GradientButton(
                      label: 'Enregistrer',
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

class _VehiclePicker extends StatelessWidget {
  const _VehiclePicker({
    required this.vehicles,
    required this.selectedId,
    required this.onChanged,
  });

  final List<Vehicle> vehicles;
  final int? selectedId;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
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