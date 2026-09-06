import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api_client.dart';
import '../../core/app_scope.dart';
import '../../core/models.dart';
import '../../core/theme.dart';
import '../../utils/format.dart';
import '../../widgets/glass.dart';
import '../../widgets/toast.dart';

/// Feuille « verre » de création / édition d'un véhicule.
class VehicleFormSheet extends StatefulWidget {
  const VehicleFormSheet({super.key, this.vehicle});

  final Vehicle? vehicle;

  @override
  State<VehicleFormSheet> createState() => _VehicleFormSheetState();
}

class _VehicleFormSheetState extends State<VehicleFormSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _immat = TextEditingController(
      text: widget.vehicle?.immatriculation ?? '');
  late final TextEditingController _marque =
      TextEditingController(text: widget.vehicle?.marque ?? '');
  late final TextEditingController _modele =
      TextEditingController(text: widget.vehicle?.modele ?? '');
  late final TextEditingController _annee = TextEditingController(
      text: widget.vehicle?.annee?.toString() ?? '');
  late final TextEditingController _km = TextEditingController(
      text: widget.vehicle?.kilometrage.toString() ?? '');
  late final TextEditingController _direction =
      TextEditingController(text: widget.vehicle?.direction ?? '');
  late final TextEditingController _affectation =
      TextEditingController(text: widget.vehicle?.affectation ?? '');

  late String _carburant = widget.vehicle?.carburant ?? 'Diesel';
  late String _statut = widget.vehicle?.statut ?? 'En service';
  bool _saving = false;

  final _carburants = ['Diesel', 'Essence', 'Électrique', 'Hybride'];
  final _statuts = ['En service', 'En maintenance', 'En panne', 'Garé'];

  @override
  void dispose() {
    _immat.dispose();
    _marque.dispose();
    _modele.dispose();
    _annee.dispose();
    _km.dispose();
    _direction.dispose();
    _affectation.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    HapticFeedback.mediumImpact();
    setState(() => _saving = true);
    try {
      final body = <String, dynamic>{
        'immatriculation': _immat.text.trim(),
        'marque': _marque.text.trim(),
        'modele': _modele.text.trim(),
        'annee': int.tryParse(_annee.text.trim()),
        'type': 'Utilitaire',
        'carburant': _carburant,
        'kilometrage': int.tryParse(_km.text.trim()) ?? 0,
        'statut': _statut,
        'direction': _direction.text.trim(),
        'affectation': _affectation.text.trim(),
      };
      if (widget.vehicle == null) {
        await app.api.post('/api/vehicles', body);
      } else {
        await app.api.put('/api/vehicles/${widget.vehicle!.id}', body);
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
          initialChildSize: 0.92,
          maxChildSize: 0.96,
          minChildSize: 0.5,
          builder: (context, scrollController) => SingleChildScrollView(
            controller: scrollController,
            padding: const EdgeInsets.fromLTRB(22, 16, 22, 30),
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
                  widget.vehicle == null
                      ? 'Ajouter un véhicule'
                      : 'Modifier ${widget.vehicle!.immatriculation}',
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
                      TextFormField(
                        controller: _immat,
                        textCapitalization: TextCapitalization.characters,
                        validator: (v) => (v == null || v.trim().length < 5)
                            ? 'Immatriculation (5 car. min)'
                            : null,
                        decoration: const InputDecoration(
                          labelText: 'Immatriculation',
                          prefixIcon:
                              Icon(Icons.badge_outlined, size: 20),
                        ),
                      ),
                      const SizedBox(height: 13),
                      Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _marque,
                              validator: (v) => (v == null || v.trim().isEmpty)
                                  ? 'Requise'
                                  : null,
                              decoration: const InputDecoration(
                                labelText: 'Marque',
                                prefixIcon:
                                    Icon(Icons.directions_car_outlined,
                                        size: 20),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextFormField(
                              controller: _modele,
                              validator: (v) => (v == null || v.trim().isEmpty)
                                  ? 'Requis'
                                  : null,
                              decoration: const InputDecoration(
                                labelText: 'Modèle',
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
                              controller: _annee,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Année',
                                prefixIcon:
                                    Icon(Icons.calendar_today_outlined,
                                        size: 18),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextFormField(
                              controller: _km,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Kilométrage',
                                prefixIcon:
                                    Icon(Icons.speed_rounded, size: 19),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      _Segmented(
                        title: 'Carburant',
                        options: _carburants,
                        selected: _carburant,
                        onChanged: (v) => setState(() => _carburant = v),
                      ),
                      const SizedBox(height: 16),
                      _Segmented(
                        title: 'Statut',
                        options: _statuts,
                        selected: _statut,
                        onChanged: (v) => setState(() => _statut = v),
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: _direction,
                        decoration: const InputDecoration(
                          labelText: 'Direction (optionnel)',
                          prefixIcon:
                              Icon(Icons.account_balance_outlined, size: 19),
                        ),
                      ),
                      const SizedBox(height: 13),
                      TextFormField(
                        controller: _affectation,
                        decoration: const InputDecoration(
                          labelText: 'Affectation / site (optionnel)',
                          prefixIcon:
                              Icon(Icons.location_on_outlined, size: 19),
                        ),
                      ),
                      const SizedBox(height: 24),
                      GradientButton(
                        label: widget.vehicle == null
                            ? 'Ajouter le véhicule'
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
}

/// Sélecteur « segments » animé (droits réservés au backend).
class _Segmented extends StatelessWidget {
  const _Segmented({
    required this.title,
    required this.options,
    required this.selected,
    required this.onChanged,
  });

  final String title;
  final List<String> options;
  final String selected;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(color: Palette.textDim, fontSize: 13.5),
        ),
        const SizedBox(height: 9),
        SizedBox(
          height: 44,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: [
              for (final o in options)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChipNex(
                    label: o,
                    selected: selected == o,
                    onTap: () => onChanged(o),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}