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

class DriversScreen extends StatefulWidget {
  const DriversScreen({super.key});

  @override
  State<DriversScreen> createState() => _DriversScreenState();
}

class _DriversScreenState extends State<DriversScreen> {
  List<Driver> _drivers = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await app.api.get('/api/drivers');
      if (!mounted) return;
      setState(() {
        _drivers = [
          for (final d in (r['drivers'] as List? ?? const []))
            if (d is Map<String, dynamic>) Driver.fromJson(d)
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

  Future<void> _add() async {
    final created = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _DriverFormSheet(),
    );
    if (created == true) {
      showNexToast(context, 'Conducteur ajouté', kind: Nest.success);
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 16, 18, 10),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Conducteurs',
                      style: TextStyle(
                        color: Palette.text,
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  ScaleTap(
                    haptic: false,
                    onTap: () {
                      pulseMedium();
                      _add();
                    },
                    child: Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        gradient: Palette.accent,
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [
                          BoxShadow(
                            color: Palette.indigo.withValues(alpha: 0.4),
                            blurRadius: 16,
                          ),
                        ],
                      ),
                      child: const Icon(Icons.person_add_alt_1_rounded,
                          color: Colors.white, size: 20),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: _loading
                  ? const ScreenSkeleton()
                  : _error != null
                      ? EmptyState(
                          icon: Icons.cloud_off_rounded,
                          title: _error!,
                        )
                      : _drivers.isEmpty
                          ? const EmptyState(
                              icon: Icons.badge_rounded,
                              title: 'Aucun conducteur',
                            )
                          : RefreshIndicator(
                              color: Palette.cyan,
                              backgroundColor: const Color(0xFF0B1120),
                              onRefresh: _load,
                              child: ListView.builder(
                                physics:
                                    const AlwaysScrollableScrollPhysics(),
                                padding: const EdgeInsets.fromLTRB(
                                    16, 4, 16, 120),
                                itemCount: _drivers.length,
                                itemBuilder: (context, i) {
                                  final d = _drivers[i];
                                  final permLeft =
                                      daysUntil(d.permisExp);
                                  return Padding(
                                    padding: const EdgeInsets.only(
                                        bottom: 10),
                                    child: GlassCard(
                                      radius: 20,
                                      padding:
                                          const EdgeInsets.all(14),
                                      child: Row(
                                        children: [
                                          Container(
                                            width: 44,
                                            height: 44,
                                            alignment: Alignment.center,
                                            decoration: BoxDecoration(
                                              gradient: Palette.accent,
                                              shape: BoxShape.circle,
                                            ),
                                            child: Text(
                                              d.fullName.characters.first
                                                  .toUpperCase(),
                                              style: const TextStyle(
                                                color: Colors.white,
                                                fontSize: 18,
                                                fontWeight:
                                                    FontWeight.w800,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 12),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment
                                                      .start,
                                              children: [
                                                Text(
                                                  d.fullName,
                                                  style: const TextStyle(
                                                    color: Palette.text,
                                                    fontSize: 15,
                                                    fontWeight:
                                                        FontWeight.w700,
                                                  ),
                                                ),
                                                const SizedBox(
                                                    height: 2),
                                                Text(
                                                  d.matricule ??
                                                      d.email ??
                                                      '—',
                                                  style: const TextStyle(
                                                      color: Palette
                                                          .textDim,
                                                      fontSize: 12),
                                                ),
                                                if (d.telephone !=
                                                        null &&
                                                    d.telephone!.isNotEmpty)
                                                  Text(
                                                    d.telephone!,
                                                    style:
                                                        const TextStyle(
                                                      color: Palette
                                                          .textMute,
                                                      fontSize: 11.5,
                                                    ),
                                                  ),
                                              ],
                                            ),
                                          ),
                                          if (d.permis != null)
                                            Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.end,
                                              children: [
                                                Text(
                                                  d.permis!,
                                                  style:
                                                      const TextStyle(
                                                    color:
                                                        Palette.cyan,
                                                    fontSize: 12,
                                                    fontWeight:
                                                        FontWeight.w800,
                                                  ),
                                                ),
                                                const SizedBox(
                                                    height: 2),
                                                Text(
                                                  permLeft == null
                                                      ? '—'
                                                      : '${permLeft < 0 ? 'expiré' : '${permLeft} j'}',
                                                  style: TextStyle(
                                                    color: permLeft !=
                                                                null &&
                                                            permLeft < 0
                                                        ? Palette.danger
                                                        : Palette
                                                            .textMute,
                                                    fontSize: 11,
                                                  ),
                                                ),
                                              ],
                                            ),
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DriverFormSheet extends StatefulWidget {
  const _DriverFormSheet();

  @override
  State<_DriverFormSheet> createState() => _DriverFormSheetState();
}

class _DriverFormSheetState extends State<_DriverFormSheet> {
  final _formKey = GlobalKey<FormState>();
  final _nom = TextEditingController();
  final _prenom = TextEditingController();
  final _matricule = TextEditingController();
  final _email = TextEditingController();
  final _telephone = TextEditingController();
  final _permis = TextEditingController();
  bool _saving = false;

  @override
  void dispose() {
    _nom.dispose();
    _prenom.dispose();
    _matricule.dispose();
    _email.dispose();
    _telephone.dispose();
    _permis.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    pulseMedium();
    setState(() => _saving = true);
    try {
      await app.api.post('/api/drivers', {
        'nom': _nom.text.trim(),
        'prenom': _prenom.text.trim(),
        'matricule': _matricule.text.trim(),
        'email': _email.text.trim(),
        'telephone': _telephone.text.trim(),
        'permis': _permis.text.trim(),
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
                'Nouveau conducteur',
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
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _nom,
                            validator: (v) => (v == null || v.trim().isEmpty)
                                ? 'Nom requis'
                                : null,
                            decoration: const InputDecoration(
                                labelText: 'Nom'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _prenom,
                            validator: (v) => (v == null || v.trim().isEmpty)
                                ? 'Prénom requis'
                                : null,
                            decoration: const InputDecoration(
                                labelText: 'Prénom'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 13),
                    TextFormField(
                      controller: _matricule,
                      decoration: const InputDecoration(
                        labelText: 'Matricule (optionnel)',
                        prefixIcon:
                            Icon(Icons.confirmation_number_outlined,
                                size: 19),
                      ),
                    ),
                    const SizedBox(height: 13),
                    TextFormField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(
                        labelText: 'Email (optionnel)',
                        prefixIcon: Icon(Icons.alternate_email_rounded,
                            size: 19),
                      ),
                    ),
                    const SizedBox(height: 13),
                    TextFormField(
                      controller: _telephone,
                      keyboardType: TextInputType.phone,
                      decoration: const InputDecoration(
                        labelText: 'Téléphone (optionnel)',
                        prefixIcon: Icon(Icons.phone_outlined, size: 19),
                      ),
                    ),
                    const SizedBox(height: 13),
                    TextFormField(
                      controller: _permis,
                      decoration: const InputDecoration(
                        labelText: 'Permis (optionnel)',
                        prefixIcon: Icon(Icons.badge_outlined, size: 19),
                      ),
                    ),
                    const SizedBox(height: 24),
                    GradientButton(
                      label: 'Ajouter',
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
}