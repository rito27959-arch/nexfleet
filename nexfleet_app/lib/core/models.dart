/// Modèles mappés sur les réponses JSON réelles de l'API NexFleet (backend Flask).

String _s(dynamic v) => v is String ? v : (v?.toString() ?? '');
double _d(dynamic v) => v is num ? v.toDouble() : (v is String ? double.tryParse(v) ?? 0 : 0);
int _i(dynamic v) => v is num ? v.toInt() : (v is String ? int.tryParse(v) ?? 0 : 0);
bool _b(dynamic v) => v is bool ? v : (v is num ? v != 0 : v == '1' || v == 'true');

class Alert {
  final String type;
  final String label;
  final int days;
  final String level;
  final String msg;
  final String vehicle;
  final String immatriculation;

  const Alert({
    required this.type,
    required this.label,
    required this.days,
    required this.level,
    required this.msg,
    required this.vehicle,
    required this.immatriculation,
  });

  bool get isDanger => level == 'danger';

  factory Alert.fromJson(Map<String, dynamic> j) => Alert(
        type: _s(j['type']),
        label: _s(j['label']),
        days: _i(j['days']),
        level: _s(j['level']),
        msg: _s(j['msg']),
        vehicle: _s(j['vehicle']),
        immatriculation: _s(j['immatriculation']),
      );
}

class Stats {
  final int total;
  final int enService;
  final int enMaintenance;
  final int enPanne;
  final int drivers;
  final int controlsMonth;
  final int vidangesCount;
  final int vidangesYear;
  final double maintenanceTotal;
  final double vidangesTotal;
  final List<Alert> alerts;
  final List<({String month, int count})> controlsByMonth;

  const Stats({
    required this.total,
    required this.enService,
    required this.enMaintenance,
    required this.enPanne,
    required this.drivers,
    required this.controlsMonth,
    required this.vidangesCount,
    required this.vidangesYear,
    required this.maintenanceTotal,
    required this.vidangesTotal,
    required this.alerts,
    required this.controlsByMonth,
  });

  int get dangerCount => alerts.where((a) => a.isDanger).length;

  factory Stats.fromJson(Map<String, dynamic> j) => Stats(
        total: _i(j['total']),
        enService: _i(j['en_service']),
        enMaintenance: _i(j['en_maintenance']),
        enPanne: _i(j['en_panne']),
        drivers: _i(j['drivers']),
        controlsMonth: _i(j['controls_month']),
        vidangesCount: _i(j['vidanges_count']),
        vidangesYear: _i(j['vidanges_year']),
        maintenanceTotal: _d(j['maintenance_total']),
        vidangesTotal: _d(j['vidanges_total']),
        alerts: [
          for (final a in (j['alerts'] as List? ?? const []))
            if (a is Map<String, dynamic>) Alert.fromJson(a)
        ],
        controlsByMonth: [
          for (final m in (j['controls_by_month'] as List? ?? const []))
            if (m is Map<String, dynamic>)
              (
                month: _s(m['month']),
                count: _i(m['count']),
              ),
        ],
      );
}

class Vehicle {
  final int id;
  final String immatriculation;
  final String marque;
  final String modele;
  final int? annee;
  final String type;
  final String carburant;
  final int kilometrage;
  final String? vignetteExp;
  final String? assuranceExp;
  final String? ctrlTechExp;
  final String? carteGriseExp;
  final String? statut;
  final String? direction;
  final String? affectation;
  final String? numChassis;
  final String? numMoteur;
  final String? carteGrise;
  final int? cv;
  final String? photo;
  final String? photoThumb;
  final List<Alert> alerts;

  const Vehicle({
    required this.id,
    required this.immatriculation,
    required this.marque,
    required this.modele,
    this.annee,
    required this.type,
    required this.carburant,
    required this.kilometrage,
    this.vignetteExp,
    this.assuranceExp,
    this.ctrlTechExp,
    this.carteGriseExp,
    this.statut,
    this.direction,
    this.affectation,
    this.numChassis,
    this.numMoteur,
    this.carteGrise,
    this.cv,
    this.photo,
    this.photoThumb,
    this.alerts = const [],
  });

  String get label => '$marque $modele';

  List<Alert> get dangerousAlerts => alerts.where((a) => a.isDanger).toList();

  factory Vehicle.fromJson(Map<String, dynamic> j) => Vehicle(
        id: _i(j['id']),
        immatriculation: _s(j['immatriculation']),
        marque: _s(j['marque']),
        modele: _s(j['modele']),
        annee: j['annee'] == null ? null : _i(j['annee']),
        type: _s(j['type']),
        carburant: _s(j['carburant']),
        kilometrage: _i(j['kilometrage']),
        vignetteExp: j['vignette_exp'] == null ? null : _s(j['vignette_exp']),
        assuranceExp:
            j['assurance_exp'] == null ? null : _s(j['assurance_exp']),
        ctrlTechExp:
            j['ctrl_tech_exp'] == null ? null : _s(j['ctrl_tech_exp']),
        carteGriseExp:
            j['carte_grise_exp'] == null ? null : _s(j['carte_grise_exp']),
        statut: j['statut'] == null ? null : _s(j['statut']),
        direction: j['direction'] == null ? null : _s(j['direction']),
        affectation: j['affectation'] == null ? null : _s(j['affectation']),
        numChassis: j['num_chassis'] == null ? null : _s(j['num_chassis']),
        numMoteur: j['num_moteur'] == null ? null : _s(j['num_moteur']),
        carteGrise: j['carte_grise'] == null ? null : _s(j['carte_grise']),
        cv: j['cv'] == null ? null : _i(j['cv']),
        photo: j['photo'] == null ? null : _s(j['photo']),
        photoThumb: j['photo_thumb'] == null ? null : _s(j['photo_thumb']),
        alerts: [
          for (final a in (j['alerts'] as List? ?? const []))
            if (a is Map<String, dynamic>) Alert.fromJson(a)
        ],
      );
}

class Vidange {
  final int id;
  final int vehicleId;
  final String date;
  final int km;
  final String huile;
  final double quantite;
  final bool filtreHuile;
  final bool filtreGasoil;
  final bool huileTransmission;
  final bool liquideRefroidissement;
  final bool liquideLaveglace;
  final int kmInterval;
  final double cout;
  final String garage;
  final String notes;
  final int prochaineKm;
  final String immatriculation;
  final String marque;
  final String modele;

  const Vidange({
    required this.id,
    required this.vehicleId,
    required this.date,
    required this.km,
    required this.huile,
    required this.quantite,
    required this.filtreHuile,
    required this.filtreGasoil,
    required this.huileTransmission,
    required this.liquideRefroidissement,
    required this.liquideLaveglace,
    required this.kmInterval,
    required this.cout,
    required this.garage,
    required this.notes,
    required this.prochaineKm,
    required this.immatriculation,
    required this.marque,
    required this.modele,
  });

  String get vehicleLabel =>
      immatriculation.isNotEmpty ? immatriculation : 'Véhicule #$vehicleId';

  List<({String label, bool on})> get consommables => [
        (label: 'Huile moteur', on: filtreHuile),
        (label: 'Filtre gasoil', on: filtreGasoil),
        (label: 'Huile transmission', on: huileTransmission),
        (label: 'Liquide refroidissement', on: liquideRefroidissement),
        (label: 'Liquide lave-glace', on: liquideLaveglace),
      ];

  factory Vidange.fromJson(Map<String, dynamic> j) => Vidange(
        id: _i(j['id']),
        vehicleId: _i(j['vehicle_id']),
        date: _s(j['date']),
        km: _i(j['km']),
        huile: _s(j['huile']),
        quantite: _d(j['quantite']),
        filtreHuile: _b(j['filtre_huile']),
        filtreGasoil: _b(j['filtre_gasoil']),
        huileTransmission: _b(j['huile_transmission']),
        liquideRefroidissement: _b(j['liquide_refroidissement']),
        liquideLaveglace: _b(j['liquide_laveglace']),
        kmInterval: _i(j['km_interval']),
        cout: _d(j['cout']),
        garage: _s(j['garage']),
        notes: _s(j['notes']),
        prochaineKm: _i(j['prochaine_km']),
        immatriculation: _s(j['immatriculation']),
        marque: _s(j['marque']),
        modele: _s(j['modele']),
      );

  Map<String, dynamic> toPayload() => {
        'vehicle_id': vehicleId,
        'date': date,
        'km': km,
        'huile': huile,
        'quantite': quantite,
        'filtre_huile': filtreHuile,
        'filtre_gasoil': filtreGasoil,
        'huile_transmission': huileTransmission,
        'liquide_refroidissement': liquideRefroidissement,
        'liquide_laveglace': liquideLaveglace,
        'km_interval': kmInterval,
        'cout': cout,
        'garage': garage,
        'notes': notes,
        'prochaine_km': prochaineKm,
      };
}

class VidangeForecast {
  final int vehicleId;
  final String immatriculation;
  final String marque;
  final String modele;
  final String? lastDate;
  final int km;
  final int kmDue;
  final int kmNow;
  final int kmLeft;
  final int? daysSince;
  final bool due;

  const VidangeForecast({
    required this.vehicleId,
    required this.immatriculation,
    required this.marque,
    required this.modele,
    this.lastDate,
    required this.km,
    required this.kmDue,
    required this.kmNow,
    required this.kmLeft,
    this.daysSince,
    required this.due,
  });

  String get label =>
      immatriculation.isNotEmpty ? immatriculation : 'Véhicule #$vehicleId';

  factory VidangeForecast.fromJson(Map<String, dynamic> j) => VidangeForecast(
        vehicleId: _i(j['vehicle_id']),
        immatriculation: _s(j['immatriculation']),
        marque: _s(j['marque']),
        modele: _s(j['modele']),
        lastDate: j['last_date'] == null ? null : _s(j['last_date']),
        km: _i(j['km']),
        kmDue: _i(j['km_due']),
        kmNow: _i(j['km_now']),
        kmLeft: _i(j['km_left']),
        daysSince: j['days_since'] == null ? null : _i(j['days_since']),
        due: _b(j['due']),
      );
}

class VidangeStats {
  final int total;
  final double costTotal;
  final int thisYear;
  final List<VidangeForecast> forecast;

  const VidangeStats({
    required this.total,
    required this.costTotal,
    required this.thisYear,
    required this.forecast,
  });

  List<VidangeForecast> get dueFirst =>
      [...forecast]..sort((a, b) {
        if (a.due != b.due) return a.due ? -1 : 1;
        return a.kmLeft.compareTo(b.kmLeft);
      });

  factory VidangeStats.fromJson(Map<String, dynamic> j) => VidangeStats(
        total: _i(j['total']),
        costTotal: _d(j['cost_total']),
        thisYear: _i(j['this_year']),
        forecast: [
          for (final f in (j['forecast'] as List? ?? const []))
            if (f is Map<String, dynamic>) VidangeForecast.fromJson(f)
        ],
      );
}

class MaintenanceItem {
  final int id;
  final int vehicleId;
  final String type;
  final String date;
  final double cout;
  final String garage;
  final String notes;
  final String immatriculation;
  final String marque;
  final String modele;

  const MaintenanceItem({
    required this.id,
    required this.vehicleId,
    required this.type,
    required this.date,
    required this.cout,
    required this.garage,
    required this.notes,
    required this.immatriculation,
    required this.marque,
    required this.modele,
  });

  String get vehicleLabel =>
      immatriculation.isNotEmpty ? immatriculation : 'Véhicule #$vehicleId';

  factory MaintenanceItem.fromJson(Map<String, dynamic> j) => MaintenanceItem(
        id: _i(j['id']),
        vehicleId: _i(j['vehicle_id']),
        type: _s(j['type']),
        date: _s(j['date']),
        cout: _d(j['cout']),
        garage: _s(j['garage']),
        notes: _s(j['notes']),
        immatriculation: _s(j['immatriculation']),
        marque: _s(j['marque']),
        modele: _s(j['modele']),
      );

  Map<String, dynamic> toPayload() => {
        'vehicle_id': vehicleId,
        'type': type,
        'date': date,
        'cout': cout,
        'garage': garage,
        'notes': notes,
      };
}

class Driver {
  final int id;
  final String nom;
  final String prenom;
  final String? matricule;
  final String? email;
  final String? telephone;
  final String? permis;
  final String? permisExp;
  final String? cni;
  final String? cniExp;

  const Driver({
    required this.id,
    required this.nom,
    required this.prenom,
    this.matricule,
    this.email,
    this.telephone,
    this.permis,
    this.permisExp,
    this.cni,
    this.cniExp,
  });

  String get fullName => '$prenom $nom'.trim();

  factory Driver.fromJson(Map<String, dynamic> j) => Driver(
        id: _i(j['id']),
        nom: _s(j['nom']),
        prenom: _s(j['prenom']),
        matricule: j['matricule'] == null ? null : _s(j['matricule']),
        email: j['email'] == null ? null : _s(j['email']),
        telephone: j['telephone'] == null ? null : _s(j['telephone']),
        permis: j['permis'] == null ? null : _s(j['permis']),
        permisExp: j['permis_exp'] == null ? null : _s(j['permis_exp']),
        cni: j['cni'] == null ? null : _s(j['cni']),
        cniExp: j['cni_exp'] == null ? null : _s(j['cni_exp']),
      );

  Map<String, dynamic> toPayload() => {
        'nom': nom,
        'prenom': prenom,
        'matricule': matricule,
        'email': email,
        'telephone': telephone,
        'permis': permis,
        'permis_exp': permisExp,
        'cni': cni,
        'cni_exp': cniExp,
      };
}

class VehicleDetail {
  final Vehicle vehicle;
  final List<Vidange> vidanges;
  final List<MaintenanceItem> maintenance;
  final double totalSpent;

  const VehicleDetail({
    required this.vehicle,
    required this.vidanges,
    required this.maintenance,
    required this.totalSpent,
  });

  factory VehicleDetail.fromJson(Map<String, dynamic> j) => VehicleDetail(
        vehicle: Vehicle.fromJson(j['vehicle'] as Map<String, dynamic>),
        vidanges: [
          for (final v in (j['vidanges'] as List? ?? const []))
            if (v is Map<String, dynamic>) Vidange.fromJson(v)
        ],
        maintenance: [
          for (final m in (j['maintenance'] as List? ?? const []))
            if (m is Map<String, dynamic>) MaintenanceItem.fromJson(m)
        ],
        totalSpent: _d(j['total_spent']),
      );
}

