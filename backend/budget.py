# -*- coding: utf-8 -*-
"""Budget & Plan de maintenance préventive.

Ce module sait lire le fichier « Plan d'achat annuel » réel de l'entreprise
(tel qu'exporté depuis leur classeur Excel de planification — feuille
« Plan d'achat annuel », trimestres I à IV, quantités + montants en FCFA) et
le convertit en lignes exploitables par l'application, afin de comparer le
budget prévisionnel au coût réellement enregistré dans NexFleet
(tables ``maintenance`` et ``vidanges``).

Aucune dépendance externe : lecture xlsx via ``io_xlsx`` (zip + XML stdlib).
"""

import re
import unicodedata
from datetime import date

import io_xlsx
from db import now

# ---------------------------------------------------------------- catégories
# Catégories standardisées communes au plan budgétaire ET au champ
# `maintenance.type` de l'application, afin que le prévisionnel et le réalisé
# puissent être comparés directement.
CATEGORIES = [
    "Moteur", "Freinage", "Pompes", "Administratif", "Vidange",
    "Pneumatique", "Tôlerie", "Batterie", "Climatisation",
    "Électronique", "Révision", "Autre",
]

# Anciens libellés (versions précédentes de l'app / saisies historiques) —
# ramenés vers la catégorie standard correspondante, sans jamais modifier
# les données existantes en base.
_ALIASES = {
    "pneus": "Pneumatique",
    "freins": "Freinage",
    "carrosserie": "Tôlerie",
}


def _strip_accents(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm_key(s):
    return _strip_accents(str(s or "")).lower().strip()


_KEYWORD_MAP = [
    (("moteur", "culasse", "embrayage"), "Moteur"),
    (("frein",), "Freinage"),
    (("pompe",), "Pompes"),
    (("dossier", "administrati", "carte grise", "visite technique", "vignette", "assurance"), "Administratif"),
    (("vidange", "huile", "graisse", "filtre", "refroidissement"), "Vidange"),
    (("pneu", "jante", "roue"), "Pneumatique"),
    (("toler", "carrosserie", "peinture", "pare brise", "pare-brise", "phare", "klaxon", "essuie"), "Tôlerie"),
    (("batter",), "Batterie"),
    (("climat",), "Climatisation"),
    (("electron",), "Électronique"),
    (("revision",), "Révision"),
]


def normalize_categorie(raw):
    """Ramène un libellé libre (catégorie budget OU type de maintenance saisi)
    vers l'une des catégories standard de ``CATEGORIES``."""
    key = _norm_key(raw)
    if not key:
        return "Autre"
    if key in _ALIASES:
        return _ALIASES[key]
    for cat in CATEGORIES:
        if _norm_key(cat) == key:
            return cat
    for keywords, cat in _KEYWORD_MAP:
        if any(kw in key for kw in keywords):
            return cat
    return "Autre"


def normalize_domaine(activite_text):
    key = _norm_key(activite_text)
    if "parc auto" in key or "parc-auto" in key:
        return "parc_auto"
    if "batiment" in key or "patrimoine" in key:
        return "batiment"
    return "autre"


# ---------------------------------------------------------------- parsing xlsx
_NUM_RE = re.compile(r"[^\d,.\-]")


def _num(v):
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = _NUM_RE.sub("", str(v).replace(",", "."))
    if not s or s in ("-", "."):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _find_year(rows):
    for row in rows[:8]:
        for cell in row:
            m = re.search(r"\b(20\d{2})\b", str(cell or ""))
            if m:
                return int(m.group(1))
    return date.today().year


def _looks_like_plan_sheet(name, rows):
    n = _norm_key(name)
    if "achat" in n or "budget" in n or "plan" in n:
        return True
    for row in rows[:10]:
        joined = _norm_key(" ".join(str(c or "") for c in row))
        if "tache" in joined and "montant" in joined:
            return True
    return False


def parse_budget_workbook(data, filename=""):
    """Analyse le classeur .xlsx et retourne (rows, meta).

    ``rows`` : liste de dicts prêts pour insertion dans ``budget_plan``.
    ``meta`` : {"annee": int, "sheet": str, "rows_found": int, "rows_skipped": int}
    """
    sheets = io_xlsx.read_xlsx_sheets(data)
    if not sheets:
        raise ValueError("Aucune feuille exploitable dans ce fichier.")

    target_name, target_rows = None, None
    for name, rows in sheets.items():
        if _looks_like_plan_sheet(name, rows):
            target_name, target_rows = name, rows
            break
    if target_rows is None:
        # à défaut, la première feuille non vide
        for name, rows in sheets.items():
            if rows:
                target_name, target_rows = name, rows
                break
    if not target_rows:
        raise ValueError("Impossible de trouver une feuille de plan de maintenance dans ce fichier.")

    annee = _find_year(target_rows)

    # localise la ligne d'en-tête ("TÂCHE" + "Montant" ou proche)
    header_idx = None
    for i, row in enumerate(target_rows[:12]):
        joined = _norm_key(" ".join(str(c or "") for c in row))
        if "tache" in joined and ("montant" in joined or "quantit" in joined):
            header_idx = i
            break
    if header_idx is None:
        header_idx = 6  # position observée dans le gabarit fourni par l'entreprise

    out_rows = []
    skipped = 0
    cur_service, cur_activite, cur_categorie = "", "", ""
    cur_domaine = "parc_auto"

    for row in target_rows[header_idx + 2:]:
        row = list(row) + [""] * max(0, 29 - len(row))
        service, activite, categorie, tache = row[0], row[1], row[2], row[3]

        if service and str(service).strip():
            cur_service = str(service).strip()
        if activite and str(activite).strip():
            cur_activite = str(activite).strip()
            cur_domaine = normalize_domaine(cur_activite)
        if categorie and str(categorie).strip():
            cur_categorie = str(categorie).strip()

        tache = str(tache or "").strip()
        upper_service = _norm_key(cur_service)
        if not tache or tache.upper().startswith("TOTAL") or "total" in upper_service and not tache:
            skipped += 1
            continue
        if _norm_key(tache).startswith("total"):
            skipped += 1
            continue

        montant_annuel = _num(row[26])
        qte_annuelle = _num(row[24])
        if montant_annuel == 0 and qte_annuelle == 0 and _num(row[8]) == 0 and _num(row[13]) == 0 \
                and _num(row[18]) == 0 and _num(row[23]) == 0:
            # ligne totalement vide (pas de budget prévu) : on la garde quand
            # même pour la visibilité du plan de travail, montants à 0.
            pass

        out_rows.append({
            "annee": annee,
            "domaine": cur_domaine,
            "service": cur_service,
            "activite": cur_activite,
            "categorie": cur_categorie,
            "categorie_std": normalize_categorie(cur_categorie or tache),
            "tache": tache,
            "q1_qte": _num(row[7]), "q1_montant": _num(row[8]),
            "q2_qte": _num(row[12]), "q2_montant": _num(row[13]),
            "q3_qte": _num(row[17]), "q3_montant": _num(row[18]),
            "q4_qte": _num(row[22]), "q4_montant": _num(row[23]),
            "qte_annuelle": qte_annuelle or (_num(row[7]) + _num(row[12]) + _num(row[17]) + _num(row[22])),
            "prix_unitaire": _num(row[25]),
            "montant_annuel": montant_annuel or (
                _num(row[8]) + _num(row[13]) + _num(row[18]) + _num(row[23])),
            "mois_concerne": str(row[27] or "").strip(),
            "regle_mensualisation": str(row[28] or "").strip(),
            "source_fichier": filename,
        })

    if not out_rows:
        raise ValueError(
            "Aucune ligne de tâche exploitable trouvée. Vérifiez qu'il s'agit bien "
            "du fichier « Plan d'achat annuel » du parc automobile."
        )

    return out_rows, {
        "annee": annee, "sheet": target_name,
        "rows_found": len(out_rows), "rows_skipped": skipped,
    }


# ---------------------------------------------------------------- persistance
def replace_budget_plan(db, annee, rows):
    db.execute("DELETE FROM budget_plan WHERE annee=?", (annee,))
    ts = now()
    for r in rows:
        db.execute(
            """INSERT INTO budget_plan
               (annee, domaine, service, activite, categorie, categorie_std, tache,
                q1_qte, q1_montant, q2_qte, q2_montant, q3_qte, q3_montant, q4_qte, q4_montant,
                qte_annuelle, prix_unitaire, montant_annuel, mois_concerne, regle_mensualisation,
                source_fichier, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["annee"], r["domaine"], r["service"], r["activite"], r["categorie"], r["categorie_std"],
             r["tache"], r["q1_qte"], r["q1_montant"], r["q2_qte"], r["q2_montant"],
             r["q3_qte"], r["q3_montant"], r["q4_qte"], r["q4_montant"], r["qte_annuelle"],
             r["prix_unitaire"], r["montant_annuel"], r["mois_concerne"], r["regle_mensualisation"],
             r["source_fichier"], ts))
    db.commit()


def _quarter_of_month(m):
    return (m - 1) // 3 + 1


def realise_par_categorie_trimestre(db, annee):
    """Coût réellement enregistré (maintenance + vidanges) par catégorie
    standard et par trimestre, pour l'année donnée."""
    out = {cat: {"q1": 0.0, "q2": 0.0, "q3": 0.0, "q4": 0.0, "total": 0.0} for cat in CATEGORIES}

    for r in db.execute(
            "SELECT type, date, cout FROM maintenance WHERE substr(date,1,4)=?", (str(annee),)):
        cat = normalize_categorie(r["type"])
        try:
            month = int(str(r["date"])[5:7])
        except (ValueError, TypeError):
            continue
        q = f"q{_quarter_of_month(month)}"
        out[cat][q] += float(r["cout"] or 0)
        out[cat]["total"] += float(r["cout"] or 0)

    for r in db.execute(
            "SELECT date, cout FROM vidanges WHERE substr(date,1,4)=?", (str(annee),)):
        try:
            month = int(str(r["date"])[5:7])
        except (ValueError, TypeError):
            continue
        q = f"q{_quarter_of_month(month)}"
        out["Vidange"][q] += float(r["cout"] or 0)
        out["Vidange"]["total"] += float(r["cout"] or 0)

    return out


def budget_summary(db, annee, domaine="parc_auto"):
    """Tableau de comparaison prévu / réalisé par catégorie pour l'année,
    plus alertes de dépassement."""
    prevu = {cat: {"q1": 0.0, "q2": 0.0, "q3": 0.0, "q4": 0.0, "total": 0.0} for cat in CATEGORIES}
    rows = db.execute(
        "SELECT categorie_std, q1_montant, q2_montant, q3_montant, q4_montant, montant_annuel "
        "FROM budget_plan WHERE annee=? AND domaine=?", (annee, domaine)).fetchall()
    has_plan = len(rows) > 0
    for r in rows:
        cat = r["categorie_std"] if r["categorie_std"] in prevu else "Autre"
        prevu[cat]["q1"] += float(r["q1_montant"] or 0)
        prevu[cat]["q2"] += float(r["q2_montant"] or 0)
        prevu[cat]["q3"] += float(r["q3_montant"] or 0)
        prevu[cat]["q4"] += float(r["q4_montant"] or 0)
        prevu[cat]["total"] += float(r["montant_annuel"] or 0)

    realise = realise_par_categorie_trimestre(db, annee)

    categories_out = []
    alerts = []
    total_prevu = total_realise = 0.0
    for cat in CATEGORIES:
        p = prevu[cat]["total"]
        rl = realise[cat]["total"]
        total_prevu += p
        total_realise += rl
        taux = (rl / p * 100) if p > 0 else (100.0 if rl > 0 else 0.0)
        ecart = p - rl
        level = "ok"
        if p > 0 and rl > p:
            level = "danger"
        elif p > 0 and taux >= 85:
            level = "warning"
        elif p == 0 and rl > 0:
            level = "warning"
        entry = {
            "categorie": cat, "prevu": round(p, 2), "realise": round(rl, 2),
            "ecart": round(ecart, 2), "taux": round(taux, 1), "level": level,
            "prevu_q": {k: round(prevu[cat][k], 2) for k in ("q1", "q2", "q3", "q4")},
            "realise_q": {k: round(realise[cat][k], 2) for k in ("q1", "q2", "q3", "q4")},
        }
        categories_out.append(entry)
        if level in ("danger", "warning") and (p > 0 or rl > 0):
            alerts.append(entry)

    alerts.sort(key=lambda e: (-1 if e["level"] == "danger" else 0, -(e["realise"] - e["prevu"])))

    return {
        "annee": annee, "domaine": domaine, "has_plan": has_plan,
        "total_prevu": round(total_prevu, 2), "total_realise": round(total_realise, 2),
        "total_ecart": round(total_prevu - total_realise, 2),
        "taux_global": round((total_realise / total_prevu * 100) if total_prevu > 0 else 0, 1),
        "categories": categories_out, "alerts": alerts,
    }


def available_years(db):
    return [r["annee"] for r in db.execute(
        "SELECT DISTINCT annee FROM budget_plan ORDER BY annee DESC")]


def prix_unitaire_moyen(db, annee, categorie_std):
    r = db.execute(
        "SELECT AVG(prix_unitaire) AS pu FROM budget_plan "
        "WHERE annee=? AND categorie_std=? AND prix_unitaire>0",
        (annee, categorie_std)).fetchone()
    return float(r["pu"]) if r and r["pu"] else 0.0
