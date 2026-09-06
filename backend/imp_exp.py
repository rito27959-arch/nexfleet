# -*- coding: utf-8 -*-
"""Import / export Excel & CSV du parc (véhicules, conducteurs, contrôles, maintenance)."""

import re
import unicodedata
from datetime import date, datetime, timedelta

from db import get_db, now
import io_xlsx
import smart_import


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s.lower())


SHEET_RULES = [
    ("vignettes", ("vignette",)),
    ("controles_tech", ("controletechnique", "controle technique", "ctexp", "expirationct")),
    ("cartes_grise", ("cartegrise", "carte grise", "cartesgrises")),
    ("permis", ("permis",)),
    ("cni", ("cni", "identite", "carteidentite", "carte identite")),
    ("vehicles", ("vehicule", "flotte", "voiture", "parc", "camion")),
    ("drivers", ("conduct", "driver", "chauffeur")),
    ("controls", ("control", "fiche", "verification")),
    ("maintenance", ("maintenance", "intervention", "atelier", "reparation")),
    ("vidanges", ("vidange", "huile", "oil")),
]

V_FIELDS = {
    "immatriculation": {"immatriculation", "immat", "immatriculations", "plaque", "plate"},
    "marque": {"marque", "brand", "marques"},
    "modele": {"modele", "model", "models"},
    "annee": {"annee", "year", "miseencirculation"},
    "type": {"type", "categorie", "genre", "typevehicule"},
    "carburant": {"carburant", "fuel", "energie"},
    "kilometrage": {"kilometrage", "km", "kilometres", "kmactuel"},
    "statut": {"statut", "etat", "status"},
    "affectation": {"affectation", "affecte", "affectee", "assignation", "affecte a", "site",
                    "service", "depot", "emplacement"},
    "direction": {"direction", "directiongenerale", "direction generale", "dir", "dirgen"},
    "vignette_exp": {"vignette", "vignetteexp", "expirationvignette", "echeancevignette"},
    "vignette_note": {"notevignette", "note vignette", "vignette note", "note de vignette"},
    "assurance_exp": {"assurance", "assuranceexp", "expirationassurance"},
    "ctrl_tech_exp": {"ct", "controletechnique", "ctexp", "ctexpiration", "controleexp"},
    "ct_note": {"notect", "note ct", "note controletechnique", "notecontrole", "note controle", "ct note"},
    "num_chassis": {"chassis", "numchassis", "numerochassis", "n chassis", "nchassis", "vin"},
    "num_moteur": {"moteur", "nummoteur", "numeromoteur", "n moteur", "nmoteur", "engine"},
    "cv": {"cv", "chevaux", "chevauxfiscaux", "puissance", "puissancecv", "nbrcv"},
    "carte_grise": {"cartegrise", "carte grise", "cg", "numcg", "numerocg", "numerocartegrise", "n cg", "n cartegrise", "ncartegrise"},
    "carte_grise_exp": {"cartegriseexp", "carte grise exp", "expirationcartegrise", "cgexp", "carterigse expiration",
                        "exp cartegrise", "expcartegrise", "dateexpirationcg", "dateexpirationcartegrise"},
    "carte_grise_note": {"notecartegrise", "note cartegrise", "note carte grise", "carte grise note", "cartegrise note"},
}
D_FIELDS = {
    "nom": {"nom", "name", "nomdefamille", "lastname"},
    "prenom": {"prenom", "firstname", "prenoms"},
    "matricule": {"matricule", "matriculeemploye", "matriculeagent", "numemploye", "employeeid", "matric"},
    "email": {"email", "mail", "courriel"},
    "telephone": {"telephone", "tel", "phone", "mobile", "portable"},
    "permis": {"permis", "npermis", "noperemis", "licence"},
    "permis_exp": {"permi sexp", "permisexp", "validitepermis", "expirationpermis", "permisexpiration"},
    "cni_exp": {"cni", "cniexp", "carteidentite", "carteid", "expirationcni", "cniexpiration", "expirecni", "expirecarte"},
}
C_FIELDS = {
    "immatriculation": {"immatriculation", "immat", "plaque", "vehicule"},
    "conducteur": {"conducteur", "chauffeur", "driver", "nomconducteur", "conduitpar"},
    "date": {"date", "jour", "datecontrole", "dateducontrole"},
    "type": {"type", "typecontrole"},
    "resultat": {"resultat", "resultatcontrole", "conformite", "statutcontrole"},
    "notes": {"notes", "observations", "remarques"},
}
M_FIELDS = {
    "immatriculation": {"immatriculation", "immat", "plaque", "vehicule"},
    "type": {"type", "intervention", "typedintervention"},
    "date": {"date", "jour", "datedintervention"},
    "cout": {"cout", "coute", "coutfcfa", "montant", "prix", "couts", "tva", "montantfcfa"},
    "garage": {"garage", "garagiste", "atelier"},
    "notes": {"notes", "observations", "remarques", "description"},
}
VG_FIELDS = {
    "immatriculation": {"immatriculation", "immat", "plaque", "vehicule"},
    "date": {"date", "jour", "datevidange", "datedelavidange"},
    "km": {"km", "kilometrage", "kmaucompteur", "kilometres", "kmcompteur",
           "kilometragealavidange", "kmalavidange", "km compteur", "kilometragevidange"},
    "km_interval": {"kmdelavidange", "kmvidange", "intervalle", "intervallevidange",
                    "kmparcourus", "kilometredelavidange", "kilometragedelavidange",
                    "distancedepuis", "distance depuis", "depuisdernierevidange",
                    "intervallekm", "intervallekms", "intervalledevidange"},
    "prochaine_km": {"prochaine", "prochainekm", "prochaine vidange", "kmprochainevidange",
                     "prochainevidangekm", "prochainevidange", "kmprochaine",
                     "kilometreprochaine", "prochaine km"},
    "huile": {"huile", "huileutilisee", "typehuile", "huilemoteur"},
    "quantite": {"quantite", "quantitehuile", "litres", "volume"},
    "filtre_huile": {"filtre", "filtrehuile", "filtre a huile", "filtreahuile",
                     "remplacementfiltre", "filtrehuilechange", "filtre huile"},
    "filtre_gasoil": {"filtre a gazoil", "filtreagazoil", "filtre gazoil", "filtregasoil",
                      "filtre diesel", "filtrediesel", "filtre a gasoil",
                      "filtreagasoil", "filtre a goz"},
    "huile_transmission": {"huile de transmission", "huiletransmission", "huile boite",
                           "huileboite", "boite de vitesses", "boitedevitesses",
                           "huile transmission", "huilepont", "huile pont",
                           "huile boite de vitesses", "huileboitedevitesses"},
    "liquide_refroidissement": {"liquide de refroidissement", "liquiderefroidissement",
                                "liquide refroidissement", "antigel",
                                "liquide refroidis", "refroidissement",
                                "liquide de refroidis"},
    "liquide_laveglace": {"liquide lave glace", "liquidelaveglace", "lave glace",
                          "laveglace", "liquide lave-glace", "liquide lavage",
                          "liquidelavage", "liquide de lavage", "liquidedelavage"},
    "cout": {"cout", "coute", "coutfcfa", "montant", "prix", "couts"},
    "garage": {"garage", "garagiste", "atelier"},
    "notes": {"notes", "observations", "remarques", "description"},
}
NOTES_SYN = {"notes", "observations", "remarques", "remarque", "commentaire", "description", "note", "details", "obser"}
VEH_DOC_DATE = {"date", "echeance", "expiration", "exp", "valablejusqu", "datelimite", "dateexpiration", "dateecheance"}
VI_FIELDS = {
    "immatriculation": {"immatriculation", "immat", "plaque", "vehicule"},
    "date": {"vignette", "vignetteexp", "expirationvignette", "datevignette", "date devignette",
             "vignette exp"} | VEH_DOC_DATE,
    "notes": NOTES_SYN,
}
CT_FIELDS = {
    "immatriculation": {"immatriculation", "immat", "plaque", "vehicule"},
    "date": {"ct", "controle technique", "controletechnique", "ctexp", "expirationct", "datect",
             "date controle", "datecontroletechnique", "validitect"} | VEH_DOC_DATE,
    "numero": {"nct", "numct", "numeropv", "n pv", "pv", "bulletin"},
    "resultat": {"resultat", "resultatct", "conformite", "avis", "decision"},
    "notes": NOTES_SYN,
}
CG_FIELDS = {
    "immatriculation": {"immatriculation", "immat", "plaque", "vehicule"},
    "numero": {"cartegrise", "carte grise", "numerocg", "numcg", "ncg", "numerocartegrise",
               "ncartegrise", "n cartegrise", "cg", "numero", "no", "num"},
    "date": {"cartegriseexp", "carte grise exp", "expirationcartegrise", "expcartegrise",
             "dateexpirationcg", "echeancecg", "expiration cg", "cg exp", "validitecg"} | VEH_DOC_DATE,
    "notes": NOTES_SYN,
}
P_FIELDS = {
    "nom": {"nom", "nomdefamille", "name", "lastname"},
    "prenom": {"prenom", "firstname", "prenoms"},
    "conducteur": {"conducteur", "chauffeur", "driver"},
    "numero": {"permis", "npermis", "noperemis", "no de permis", "n permis", "numeropermis",
               "licence", "numero", "no", "num"},
    "date": {"validite", "validitepermis", "permisexp", "expirationpermis", "permis valable",
             "valablejusqu", "permisexpiration", "dateexpirationpermis"} | VEH_DOC_DATE,
    "notes": NOTES_SYN,
}
CNI_FIELDS = {
    "nom": {"nom", "nomdefamille", "name", "lastname"},
    "prenom": {"prenom", "firstname", "prenoms"},
    "conducteur": {"conducteur", "chauffeur", "driver"},
    "numero": {"cni", "n cni", "ncni", "numerocni", "cartecni", "ncartecni", "numerocarte",
               "carte identite", "carteidentite", "numero", "no", "num"},
    "date": {"cni", "expirationcni", "cniexp", "cni expiration", "dateexpirationcni",
             "expiration carte", "expiration cnib", "expirationcarteidentite"} | VEH_DOC_DATE,
    "notes": NOTES_SYN,
}

KIND_LABEL = {
    "vehicles": "véhicules", "drivers": "conducteurs",
    "controls": "contrôles", "maintenance": "interventions",
    "vidanges": "vidanges",
    "vignettes": "vignettes", "controles_tech": "contrôles techniques",
    "cartes_grise": "cartes grises", "permis": "permis", "cni": "cartes d'identité",
}


def _header_map(headers, fields):
    out = {}
    for i, h in enumerate(headers):
        n = norm(h)
        for field, syn in fields.items():
            if n in syn:
                out[field] = i
                break
    return out


def detect_sheet(name):
    n = norm(name)
    for kind, keys in SHEET_RULES:
        if any(k in n for k in keys):
            return kind
    return None


def _parse_date(value):
    v = str(value or "").strip()
    if not v:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return v
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v[:10], fmt).date().isoformat()
        except ValueError:
            pass
    if re.match(r"^\d{5}$", v):
        try:
            return (date(1899, 12, 30) + timedelta(days=int(v))).isoformat()
        except (OverflowError, ValueError):
            pass
    # moteur intelligent : dates en toutes lettres, formats exotiques, séries Excel…
    return smart_import.parse_any_date(v)


def _clean_num(value):
    """Nettoie un montant : retire devise (FCFA, CFA, F, Fr…), séparateurs de milliers
    (espaces, apostrophes) tout en gardant l'éventuel texte en toutes lettres intact."""
    v = str(value or "").strip().replace("\u00a0", " ")
    v = re.sub(r"(?i)\b(fcfa|cfa|francs?|frs?|f[.\s]*)\s*$", "", v).strip()
    v = re.sub(r"(?i)\b(fcfa|cfa|francs?|frs?)\b", "", v).strip()
    if re.search(r"\d", v) and not re.search(r"[a-zà-ÿ]", v, re.I):
        v = re.sub(r"\s+", "", v)
    return v.replace("'", "")


def _fr_float(v):
    """Float avec conventions françaises : '1.234.567' -> 1234567, '12,50' -> 12.5."""
    if not v:
        return None
    if re.match(r"^-?\d{1,3}([.,]\d{3})+$", v):
        v = v.replace(".", "").replace(",", "")
    elif re.match(r"^-?\d+[.,]\d+$", v):
        v = v.replace(",", ".")
    else:
        v = v.replace(",", "").replace(".", "")
    try:
        return float(v)
    except ValueError:
        return None


def _parse_int(value):
    v = _clean_num(value)
    if not v:
        return 0
    f = _fr_float(v)
    if f is not None:
        return int(f)
    # nombre écrit en toutes lettres (« quinze mille »)
    w = smart_import.words_to_int(value)
    return w if w is not None else 0


def _parse_float(value):
    v = _clean_num(value)
    if not v:
        return 0
    f = _fr_float(v)
    if f is not None:
        return f
    w = smart_import.words_to_int(value)
    return float(w) if w is not None else 0


def _row_to_dict(headers, row, fields):
    out = {}
    for field, idx in _header_map(headers, fields).items():
        if idx < len(row):
            out[field] = str(row[idx]).strip() if row[idx] is not None else ""
    return out


def _combined_map(headers, rows, fields):
    """Cartographie en-têtes->champs : correspondance exacte d'en-tête d'abord,
    puis détection par contenu (moteur intelligent) pour les colonnes restantes."""
    out = {}
    used = set()
    head = _header_map(headers, fields)
    for field, idx in head.items():
        out[field] = idx
        used.add(idx)
    remaining = {f: s for f, s in fields.items() if f not in out}
    if not remaining:
        return out
    smart = smart_import.map_columns(headers, rows, remaining)
    for field, idx in smart.items():
        if idx not in used and field not in out:
            out[field] = idx
            used.add(idx)
    return out


# ------------------------------------------------------------------ import
def _upsert_vehicle(data, report):
    imm = (data.get("immatriculation") or "").strip().upper()
    marque = (data.get("marque") or "").strip()
    modele = (data.get("modele") or "").strip()
    if len(imm) < 5:
        report["errors"].append("Immatriculation invalide (5 caractères min).")
        return
    if not marque or not modele:
        report["errors"].append("Marque et modèle requis.")
        return
    db = get_db()
    vals = {
        "marque": marque, "modele": modele,
        "annee": _parse_int(data.get("annee")) or None,
        "type": data.get("type") or "Utilitaire",
        "carburant": data.get("carburant") or "Diesel",
        "kilometrage": max(_parse_int(data.get("kilometrage")), 0),
        "vignette_exp": _parse_date(data.get("vignette_exp")),
        "assurance_exp": _parse_date(data.get("assurance_exp")),
        "ctrl_tech_exp": _parse_date(data.get("ctrl_tech_exp")),
        "statut": data.get("statut") or "En service",
        "direction": (data.get("direction") or "").strip() or None,
        "affectation": (data.get("affectation") or "").strip() or None,
        "num_chassis": (data.get("num_chassis") or "").strip() or None,
        "num_moteur": (data.get("num_moteur") or "").strip() or None,
        "cv": _parse_int(data.get("cv")) or None,
        "carte_grise": (data.get("carte_grise") or "").strip() or None,
        "carte_grise_exp": _parse_date(data.get("carte_grise_exp")),
        "vignette_note": (data.get("vignette_note") or "").strip() or None,
        "ct_note": (data.get("ct_note") or "").strip() or None,
        "carte_grise_note": (data.get("carte_grise_note") or "").strip() or None,
    }
    annee = vals["annee"]
    if annee is not None and not (1970 <= annee <= 2100):
        report["errors"].append(f"{imm} : année invalide.")
        return
    existing = db.execute("SELECT id FROM vehicles WHERE immatriculation=?", (imm,)).fetchone()
    try:
        if existing:
            db.execute(
                """UPDATE vehicles SET marque=?, modele=?, annee=?, type=?, carburant=?,
                   kilometrage=?, vignette_exp=?, assurance_exp=?, ctrl_tech_exp=?, statut=?,
                   direction=?, affectation=?, num_chassis=?, num_moteur=?, carte_grise=?,
                   carte_grise_exp=?, cv=?, vignette_note=?, ct_note=?, carte_grise_note=? WHERE id=?""",
                (vals["marque"], vals["modele"], vals["annee"], vals["type"], vals["carburant"],
                 vals["kilometrage"], vals["vignette_exp"], vals["assurance_exp"],
                 vals["ctrl_tech_exp"], vals["statut"], vals["direction"],
                 vals["affectation"], vals["num_chassis"], vals["num_moteur"],
                 vals["carte_grise"], vals["carte_grise_exp"], vals["cv"],
                 vals["vignette_note"], vals["ct_note"], vals["carte_grise_note"], existing["id"]))
            db.commit()
            report["updated"] += 1
            vid = existing["id"]
        else:
            cur = db.execute(
                """INSERT INTO vehicles (immatriculation, marque, modele, annee, type, carburant,
                   kilometrage, vignette_exp, assurance_exp, ctrl_tech_exp, statut, direction,
                   affectation, num_chassis, num_moteur, carte_grise, carte_grise_exp, cv,
                   vignette_note, ct_note, carte_grise_note, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (imm, vals["marque"], vals["modele"], vals["annee"], vals["type"], vals["carburant"],
                 vals["kilometrage"], vals["vignette_exp"], vals["assurance_exp"],
                 vals["ctrl_tech_exp"], vals["statut"], vals["direction"],
                 vals["affectation"], vals["num_chassis"], vals["num_moteur"],
                 vals["carte_grise"], vals["carte_grise_exp"], vals["cv"],
                 vals["vignette_note"], vals["ct_note"], vals["carte_grise_note"], now()))
            db.commit()
            report["created"] += 1
            vid = cur.lastrowid
    except Exception as e:
        db.rollback()
        report["errors"].append(f"{imm} : {e}")
        vid = None
    finally:
        db.close()
    return vid


def _upsert_driver(data, report):
    nom = (data.get("nom") or "").strip()
    prenom = (data.get("prenom") or "").strip()
    if not nom or not prenom:
        report["errors"].append("Nom et prénom requis.")
        return
    db = get_db()
    email = (data.get("email") or "").strip()
    existing = None
    if email:
        existing = db.execute("SELECT id FROM drivers WHERE email=?", (email,)).fetchone()
    if existing is None:
        existing = db.execute("SELECT id FROM drivers WHERE nom=? AND prenom=?",
                              (nom, prenom)).fetchone()
    try:
        if existing:
            db.execute(
                "UPDATE drivers SET nom=?, prenom=?, matricule=?, email=?, telephone=?, permis=?, permis_exp=?, cni_exp=? WHERE id=?",
                (nom, prenom, data.get("matricule") or "", email, data.get("telephone") or "",
                 data.get("permis") or "", _parse_date(data.get("permis_exp")), _parse_date(data.get("cni_exp")), existing["id"]))
            db.commit()
            report["updated"] += 1
        else:
            db.execute(
                "INSERT INTO drivers (nom, prenom, matricule, email, telephone, permis, permis_exp, cni_exp, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (nom, prenom, data.get("matricule") or "", email, data.get("telephone") or "",
                 data.get("permis") or "", _parse_date(data.get("permis_exp")), _parse_date(data.get("cni_exp")), now()))
            db.commit()
            report["created"] += 1
    except Exception as e:
        db.rollback()
        report["errors"].append(f"{prenom} {nom} : {e}")
    finally:
        db.close()


def _find_vehicle_by_imm(db, imm):
    if not imm:
        return None
    return db.execute("SELECT id FROM vehicles WHERE immatriculation=?", (imm,)).fetchone()


def _find_driver(db, ref):
    ref = (ref or "").strip()
    if not ref:
        return None
    if "@" in ref:
        return db.execute("SELECT id FROM drivers WHERE email=?", (ref,)).fetchone()
    parts = [p for p in ref.replace(",", " ").split() if p]
    if len(parts) >= 2:
        return db.execute("SELECT id FROM drivers WHERE prenom=? AND nom=?",
                          (parts[0], " ".join(parts[1:]))).fetchone()
    return db.execute("SELECT id FROM drivers WHERE nom=? OR prenom=?", (ref, ref)).fetchone()


def _insert_control(data, report):
    db = get_db()
    v = _find_vehicle_by_imm(db, (data.get("immatriculation") or "").strip().upper())
    if v is None:
        report["errors"].append("Véhicule introuvable (immatriculation).")
        db.close()
        return
    d = _find_driver(db, data.get("conducteur"))
    try:
        db.execute(
            "INSERT INTO controls (vehicle_id, driver_id, date, type, resultat, notes, items, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (v["id"], d["id"] if d else None,
             _parse_date(data.get("date")) or date.today().isoformat(),
             data.get("type") or "Contrôle technique",
             data.get("resultat") or "En cours",
             (data.get("notes") or "").strip(), None, now()))
        db.commit()
        report["created"] += 1
    except Exception as e:
        db.rollback()
        report["errors"].append(f"contrôle : {e}")
    finally:
        db.close()


def _insert_maintenance(data, report):
    db = get_db()
    v = _find_vehicle_by_imm(db, (data.get("immatriculation") or "").strip().upper())
    if v is None:
        report["errors"].append("Véhicule introuvable (immatriculation).")
        db.close()
        return
    try:
        db.execute(
            "INSERT INTO maintenance (vehicle_id, type, date, cout, garage, notes, created_at) VALUES (?,?,?,?,?,?,?)",
            (v["id"], data.get("type") or "Révision",
             _parse_date(data.get("date")) or date.today().isoformat(),
             _parse_float(data.get("cout")), data.get("garage") or "",
             (data.get("notes") or "").strip(), now()))
        db.commit()
        report["created"] += 1
    except Exception as e:
        db.rollback()
        report["errors"].append(f"intervention : {e}")
    finally:
        db.close()


def _insert_vidange(data, report):
    db = get_db()
    v = _find_vehicle_by_imm(db, (data.get("immatriculation") or "").strip().upper())
    if v is None:
        report["errors"].append("Véhicule introuvable (immatriculation).")
        db.close()
        return
    km = max(_parse_int(data.get("km")), 0)
    km_interval = max(_parse_int(data.get("km_interval")), 0)
    prochaine = max(_parse_int(data.get("prochaine_km")), 0)
    if km_interval:
        prochaine = km + km_interval
    elif not prochaine and km:
        try:
            from db import get_setting
            interval = max(500, int(get_setting("forecast_km", "10000")))
        except (ValueError, TypeError):
            interval = 10000
        prochaine = km + interval
    filtre_huile = 1 if norm(data.get("filtre_huile")) in ("oui", "1", "yes", "true", "vrai", "x", "filtre", "filtrehuile") else 0
    try:
        db.execute(
            """INSERT INTO vidanges (vehicle_id, date, km, huile, quantite, filtre,
               filtre_huile, filtre_gasoil, huile_transmission,
               liquide_refroidissement, liquide_laveglace, km_interval,
               cout, garage, notes, prochaine_km, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (v["id"], _parse_date(data.get("date")) or date.today().isoformat(), km,
             data.get("huile") or "", _parse_float(data.get("quantite")),
             filtre_huile, filtre_huile,
             1 if norm(data.get("filtre_gasoil")) in ("oui", "1", "yes", "true", "vrai", "x") else 0,
             1 if norm(data.get("huile_transmission")) in ("oui", "1", "yes", "true", "vrai", "x") else 0,
             1 if norm(data.get("liquide_refroidissement")) in ("oui", "1", "yes", "true", "vrai", "x") else 0,
             1 if norm(data.get("liquide_laveglace")) in ("oui", "1", "yes", "true", "vrai", "x") else 0,
             km_interval,
             _parse_float(data.get("cout")), data.get("garage") or "",
             (data.get("notes") or "").strip(), prochaine, now()))
        db.commit()
        report["created"] += 1
    except Exception as e:
        db.rollback()
        report["errors"].append(f"vidange : {e}")
    finally:
        db.close()


def _apply_vehicle_doc(data, report, mapping, label):
    """Met à jour les échéances / documents d'un véhicule (vignette, CT, carte grise).

    mapping : {champ_fichier: (colonne_db, is_date)}.
    """
    imm = (data.get("immatriculation") or "").strip().upper()
    if len(imm) < 5:
        report["errors"].append(f"{label} : immatriculation invalide (5 caractères min).")
        return
    db = get_db()
    v = _find_vehicle_by_imm(db, imm)
    if v is None:
        report["errors"].append(f"{label} : véhicule introuvable ({imm}).")
        db.close()
        return
    cols, vals = [], []
    for key, (col, is_date) in mapping.items():
        raw = (data.get(key) or "").strip()
        if not raw:
            continue
        val = _parse_date(raw) if is_date else raw
        if val:
            cols.append(col)
            vals.append(val)
    if not cols:
        db.close()
        return
    try:
        db.execute("UPDATE vehicles SET " + ", ".join(f"{c}=?" for c in cols) + " WHERE id=?",
                   vals + [v["id"]])
        db.commit()
        report["updated"] += 1
    except Exception as e:
        db.rollback()
        report["errors"].append(f"{imm} : {e}")
    finally:
        db.close()


def _apply_vignettes(data, report):
    _apply_vehicle_doc(data, report, {
        "date": ("vignette_exp", True),
        "notes": ("vignette_note", False),
    }, "vignette")


def _apply_controles_tech(data, report):
    _apply_vehicle_doc(data, report, {
        "date": ("ctrl_tech_exp", True),
        "notes": ("ct_note", False),
    }, "contrôle technique")


def _apply_cartes_grise(data, report):
    _apply_vehicle_doc(data, report, {
        "numero": ("carte_grise", False),
        "date": ("carte_grise_exp", True),
        "notes": ("carte_grise_note", False),
    }, "carte grise")


def _apply_driver_doc(data, report, mapping, label):
    """Met à jour les documents d'un conducteur (permis, CNI)."""
    nom = (data.get("nom") or "").strip()
    prenom = (data.get("prenom") or "").strip()
    ref = (data.get("conducteur") or "").strip()
    db = get_db()
    d = None
    if ref:
        d = _find_driver(db, ref)
    if d is None and nom and prenom:
        d = db.execute("SELECT id FROM drivers WHERE nom=? AND prenom=?",
                       (nom, prenom)).fetchone()
    if d is None:
        report["errors"].append(f"{label} : conducteur introuvable ({prenom} {nom}).")
        db.close()
        return
    cols, vals = [], []
    for key, (col, is_date) in mapping.items():
        raw = (data.get(key) or "").strip()
        if not raw:
            continue
        val = _parse_date(raw) if is_date else raw
        if val:
            cols.append(col)
            vals.append(val)
    if not cols:
        db.close()
        return
    try:
        db.execute("UPDATE drivers SET " + ", ".join(f"{c}=?" for c in cols) + " WHERE id=?",
                   vals + [d["id"]])
        db.commit()
        report["updated"] += 1
    except Exception as e:
        db.rollback()
        report["errors"].append(f"{prenom} {nom} : {e}")
    finally:
        db.close()


def _apply_permis(data, report):
    _apply_driver_doc(data, report, {
        "numero": ("permis", False),
        "date": ("permis_exp", True),
        "notes": ("permis_note", False),
    }, "permis")


def _apply_cni(data, report):
    _apply_driver_doc(data, report, {
        "numero": ("cni", False),
        "date": ("cni_exp", True),
        "notes": ("cni_note", False),
    }, "carte d'identité")


_HANDLERS = {
    "vehicles": ("vehicles", _upsert_vehicle, V_FIELDS, "véhicule"),
    "drivers": ("drivers", _upsert_driver, D_FIELDS, "conducteur"),
    "controls": ("controls", _insert_control, C_FIELDS, "contrôle"),
    "maintenance": ("maintenance", _insert_maintenance, M_FIELDS, "intervention"),
    "vidanges": ("vidanges", _insert_vidange, VG_FIELDS, "vidange"),
    "vignettes": ("vignettes", _apply_vignettes, VI_FIELDS, "vignette"),
    "controles_tech": ("controles_tech", _apply_controles_tech, CT_FIELDS, "contrôle technique"),
    "cartes_grise": ("cartes_grise", _apply_cartes_grise, CG_FIELDS, "carte grise"),
    "permis": ("permis", _apply_permis, P_FIELDS, "permis"),
    "cni": ("cni", _apply_cni, CNI_FIELDS, "carte d'identité"),
}

ALL_FIELDS = {
    "vehicles": V_FIELDS, "drivers": D_FIELDS,
    "controls": C_FIELDS, "maintenance": M_FIELDS, "vidanges": VG_FIELDS,
    "vignettes": VI_FIELDS, "controles_tech": CT_FIELDS,
    "cartes_grise": CG_FIELDS, "permis": P_FIELDS, "cni": CNI_FIELDS,
}


def analyze_file(raw_bytes, filename):
    """Analyse un fichier et retourne la détection intelligentes des données contenues."""
    name = (filename or "").lower()
    sheets = {}
    try:
        if name.endswith(".xlsx"):
            sheets = io_xlsx.read_xlsx_sheets(raw_bytes)
        elif name.endswith(".csv"):
            text = raw_bytes.decode("utf-8-sig", errors="replace")
            import csv as _csv
            sample = text.splitlines()[:10]
            dialect = _csv.Sniffer().sniff("\n".join(sample), delimiters=";,") if sample else None
            rows = list(_csv.reader(text.splitlines(), dialect or _csv.excel))
            sheets = {"Import": rows}
        else:
            return None, "Format non supporté. Utilisez .xlsx ou .csv."
    except Exception as e:
        return None, f"Impossible de lire le fichier : {e}"

    results = []
    for sheet_name, rows in sheets.items():
        if not rows or len(rows) < 2:
            continue
        headers = [str(c) for c in rows[0]]
        detected_kind = detect_sheet(sheet_name)
        smart_kind = False
        if detected_kind is None:
            detected_kind = _infer_kind(headers)
        if detected_kind is None:
            detected_kind, _ = smart_import.detect_kind(headers, rows[1:], ALL_FIELDS)
            smart_kind = detected_kind is not None
        if detected_kind and detected_kind in ALL_FIELDS:
            fields_map = ALL_FIELDS[detected_kind]
            fmap = _combined_map(headers, rows[1:], fields_map)
            mapped = {headers[idx]: field for field, idx in fmap.items() if idx < len(headers)}
            unmapped = [h for i, h in enumerate(headers) if i not in fmap.values()]

            # colonnes dates détectées (utile pour l'aperçu)
            date_cols = [field for field in fields_map if field in fmap and field.endswith(("_exp",))
                         or field in fmap and field in ("date", "prochaine_km")]

            sample_rows = []
            for row in rows[1:6]:
                r = {}
                for ci, h in enumerate(headers):
                    if ci < len(row):
                        r[h] = str(row[ci])[:60] if row[ci] is not None else ""
                sample_rows.append(r)

            results.append({
                "sheet": sheet_name,
                "detected_type": detected_kind,
                "type_label": KIND_LABEL.get(detected_kind, detected_kind),
                "total_rows": len(rows) - 1,
                "columns": headers,
                "mapped_fields": mapped,
                "unmapped_columns": unmapped,
                "date_fields": date_cols,
                "smart": smart_kind,
                "sample_rows": sample_rows,
            })

    if not results:
        return None, "Aucune donnée détectée dans le fichier."

    return {"sheets": results, "filename": filename}, None


def import_workbook(data):
    """Analyse un .xlsx et insère / met à jour les entités. Retourne un résumé."""
    return import_sheets(io_xlsx.read_xlsx_sheets(data))


def import_sheets(sheets):
    summary = {k: {"created": 0, "updated": 0, "errors": []} for k in _HANDLERS}
    smart_used = []

    for sheet_name, rows in sheets.items():
        if not rows:
            continue
        kind = detect_sheet(sheet_name)
        if kind is None:
            kind = _infer_kind(rows[0])
        headers = [str(c) for c in rows[0]]
        if kind is None:
            # détection par contenu (en-têtes génériques, colonnes mélangées…)
            kind_now, fmap = smart_import.detect_kind(headers, rows[1:], ALL_FIELDS)
            if kind_now:
                kind = kind_now
                smart_used.append(sheet_name)
        if kind not in _HANDLERS:
            continue
        handler = _HANDLERS[kind]
        fmap = _combined_map(headers, rows[1:], handler[2])
        for ri, raw in enumerate(rows[1:], 2):
            data = {}
            for field, idx in fmap.items():
                if idx < len(raw):
                    data[field] = str(raw[idx]).strip() if raw[idx] is not None else ""
            if not any(v for v in data.values()):
                continue
            errors_before = len(summary[kind]["errors"])
            handler[1](data, summary[kind])
            if len(summary[kind]["errors"]) > errors_before:
                summary[kind]["errors"][-1] = f"Ligne {ri} — {summary[kind]['errors'][-1]}"

    total_created = sum(v["created"] for v in summary.values())
    total_updated = sum(v["updated"] for v in summary.values())
    total_errors = sum(len(v["errors"]) for v in summary.values())
    return {
        "summary": summary,
        "total_created": total_created,
        "total_updated": total_updated,
        "total_errors": total_errors,
        "sheets": list(sheets.keys()),
        "smart_detected": smart_used,
    }


def _infer_kind(headers):
    n = " ".join(norm(h) for h in headers)
    names = [norm(h) for h in headers]
    # signature documents / échéances : colonnes dédiées (sauf si le fichier est une
    # fiche complète de véhicule ou de conducteur, qui prime sur la signature).
    if not any(k in n for k in ("matricule", "email", "telephone", "mobile",
                                "annee", "kilometrage", "carburant", "modele", "affectation")):
        doc_sigs = [
            ("vignettes", ("vignette",)),
            ("controles_tech", ("controletechnique", "controle technique", "ctexp", "expirationct", "validitect")),
            ("cartes_grise", ("cartegrise", "carte grise", "cartesgrises")),
            ("permis", ("permis",)),
            ("cni", ("cni", "carteidentite", "carte identite", "identitenationale",
                     "cniexpiration", "expirationcni")),
        ]
        for kind, keys in doc_sigs:
            if any(k in n for k in keys):
                return kind
        if any(x == "ct" or x.startswith("datect") or x == "nct" for x in names):
            return "controles_tech"

    # fiche complète : le type gagnant est celui qui « reconnaît » le plus de champs,
    # en excluant les synonymes trop courts (2 lettres) sujets au faux positiv« s »c't ».
    counts = {}
    for kind, fields in (("vehicles", V_FIELDS), ("drivers", D_FIELDS),
                         ("controls", C_FIELDS), ("maintenance", M_FIELDS),
                         ("vidanges", VG_FIELDS)):
        counts[kind] = sum(
            1 for field in fields
            for s in fields[field] if len(s) >= 3 and s in n)
    best = max(counts, key=lambda k: (counts[k], -list(counts).index(k)))
    return best if counts[best] >= 3 else None


# ------------------------------------------------------------------ export
def export_sheets():
    """Construit les feuilles d'export du parc complet."""
    db = get_db()
    vehs = [dict(r) for r in db.execute("SELECT * FROM vehicles ORDER BY marque, modele").fetchall()]
    drvs = [dict(r) for r in db.execute("SELECT * FROM drivers ORDER BY nom, prenom").fetchall()]
    ctrls = [dict(r) for r in db.execute(
        """SELECT c.date, c.type, c.resultat, c.notes, v.immatriculation,
                  (d.prenom || ' ' || d.nom) AS conducteur
           FROM controls c
           LEFT JOIN vehicles v ON v.id = c.vehicle_id
           LEFT JOIN drivers d ON d.id = c.driver_id
           ORDER BY c.date DESC""").fetchall()]
    mnts = [dict(r) for r in db.execute(
        """SELECT m.date, m.type, m.cout, m.garage, m.notes, v.immatriculation
           FROM maintenance m LEFT JOIN vehicles v ON v.id = m.vehicle_id
           ORDER BY m.date DESC""").fetchall()]
    vgs = [dict(r) for r in db.execute(
        """SELECT vg.date, vg.km, vg.huile, vg.quantite, vg.filtre, vg.cout, vg.garage,
                  vg.notes, vg.prochaine_km, v.immatriculation
           FROM vidanges vg LEFT JOIN vehicles v ON v.id = vg.vehicle_id
           ORDER BY vg.date DESC, vg.id DESC""").fetchall()]
    db.close()

    vh = [["Immatriculation", "Marque", "Modèle", "Année", "Type", "Carburant",
           "Kilométrage", "Statut", "Direction", "Affectation", "Échéance vignette", "Note vignette",
           "Échéance assurance", "Échéance contrôle technique", "Note CT", "N° Châssis", "N° Moteur",
           "N° Carte grise", "Exp. carte grise", "Note carte grise", "CV"]]
    for v in vehs:
        vh.append([v["immatriculation"], v["marque"], v["modele"], v["annee"], v["type"],
                   v["carburant"], v["kilometrage"], v["statut"], v.get("direction") or "",
                   v["affectation"], v["vignette_exp"], v.get("vignette_note") or "",
                   v["assurance_exp"], v["ctrl_tech_exp"], v.get("ct_note") or "",
                   v.get("num_chassis") or "", v.get("num_moteur") or "", v.get("carte_grise") or "",
                   v.get("carte_grise_exp") or "", v.get("carte_grise_note") or "", v.get("cv") or ""])

    dh = [["Nom", "Prénom", "Matricule", "Email", "Téléphone", "Permis", "Validité permis",
           "Note permis", "N° CNI", "Expiration CNI", "Note CNI"]]
    for d in drvs:
        dh.append([d["nom"], d["prenom"], d["matricule"], d["email"], d["telephone"],
                   d["permis"], d["permis_exp"], d.get("permis_note") or "",
                   d.get("cni") or "", d.get("cni_exp") or "", d.get("cni_note") or ""])

    ch = [["Immatriculation", "Conducteur", "Date", "Type", "Résultat", "Observations"]]
    for c in ctrls:
        ch.append([c["immatriculation"], c["conducteur"], c["date"], c["type"],
                   c["resultat"], c["notes"]])

    mh = [["Immatriculation", "Date", "Type", "Coût (FCFA)", "Garage", "Observations"]]
    for m in mnts:
        mh.append([m["immatriculation"], m["date"], m["type"], m["cout"], m["garage"], m["notes"]])

    vgh = [["Immatriculation", "Date", "Km", "Intervalle", "Prochaine vidange (km)",
            "Huile", "Quantité (L)", "Filtre à huile", "Filtre à gazoil",
            "Huile transmission", "Liquide refroidissement", "Liquide lave-glace",
            "Coût (FCFA)", "Garage", "Observations"]]
    for g in vgs:
        vgh.append([g["immatriculation"], g["date"], g["km"], g.get("km_interval") or "",
                    g["prochaine_km"], g["huile"], g["quantite"],
                    "Oui" if (g.get("filtre_huile") or g.get("filtre")) else "",
                    "Oui" if g.get("filtre_gasoil") else "",
                    "Oui" if g.get("huile_transmission") else "",
                    "Oui" if g.get("liquide_refroidissement") else "",
                    "Oui" if g.get("liquide_laveglace") else "",
                    g["cout"], g["garage"], g["notes"]])

    return {"Véhicules": vh, "Conducteurs": dh, "Contrôles": ch, "Maintenance": mh,
            "Vidanges": vgh}
