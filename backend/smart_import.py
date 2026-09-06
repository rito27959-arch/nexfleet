# -*- coding: utf-8 -*-
"""Moteur d'import intelligent : détection par contenu, en-têtes flous, dates en toutes lettres.

Permet de comprendre "n'importe quel" fichier : en-têtes génériques, colonnes mélangées,
dates écrites en toutes lettres (« quinze juillet deux mille vingt-trois »), numériques
avec séparateurs, plaques d'immatriculation, etc.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

# ---------------------------------------------------------------- normalisation
def _norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _words(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.split(r"[^a-z0-9]+", s.lower())


# ---------------------------------------------------------------- nombres en toutes lettres
_UNITS = {
    "zero": 0, "un": 1, "une": 1, "premier": 1, "premiere": 1,
    "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
    "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13,
    "quatorze": 14, "quinze": 15, "seize": 16,
    "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60,
    "deuxcent": 200, "troiscent": 300, "quatrecent": 400, "cinqcent": 500,
    "sixcent": 600, "septcent": 700, "huitcent": 800, "neufcent": 900,
    "cent": 100, "cents": 100, "mille": 1000, "million": 1000000, "millions": 1000000,
    "milliard": 1000000000, "milliards": 1000000000,
}


def words_to_int(text):
    """Convertit un nombre écrit en toutes lettres en entier. 'quatre-vingt-dix-neuf' -> 99.

    Gère : unites/dizaines composées, soixante-dix, quatre-vingt, quatre-vingt-dix, mille, millions.
    Retourne None si le texte n'est pas un nombre en toutes lettres valide.
    """
    if not text:
        return None
    # "vingt et un" -> "vingt un"
    toks = [t for t in re.sub(r"\bet\b", " ", str(text).lower().replace("-", " ")).split() if t]
    if not toks:
        return None
    vals = []
    i = 0
    n = len(toks)

    def push(v):
        vals.append(v)

    seen_known = False
    while i < n:
        t = toks[i]
        known = False
        # quatre-vingt[-X] / quatre-vingt-dix
        if t == "quatre" and i + 1 < n and toks[i + 1] == "vingt":
            if i + 2 < n and toks[i + 2] == "dix":
                push(90); i += 3; known = True; seen_known = True; continue
            if i + 2 < n and toks[i + 2] in _UNITS and _UNITS[toks[i + 2]] <= 9:
                push(80 + _UNITS[toks[i + 2]]); i += 3; known = True; seen_known = True; continue
            push(80); i += 2; known = True; seen_known = True; continue
        # soixante-dix / soixante-et-onze ... soixante-dix-neuf
        if t == "soixante" and i + 1 < n:
            nxt = toks[i + 1]
            if nxt == "dix" and i + 2 < n and toks[i + 2] in _UNITS and _UNITS[toks[i + 2]] <= 9:
                push(70 + _UNITS[toks[i + 2]]); i += 3; known = True; seen_known = True; continue
            if nxt == "dix":
                push(70); i += 2; known = True; seen_known = True; continue
            if nxt in ("onze", "douze", "treize", "quatorze", "quinze", "seize"):
                m = {"onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16}[nxt]
                if i + 2 < n and toks[i + 2] in _UNITS and _UNITS[toks[i + 2]] == 11:  # soixante-et-onze
                    pass
                push(60 + m); i += 2; known = True; seen_known = True; continue
        # dizaine + unite : vingt-trois, trente-cinq...
        if t in ("vingt", "trente", "quarante", "cinquante", "soixante") and i + 1 < n \
                and toks[i + 1] in _UNITS and _UNITS[toks[i + 1]] <= 9 and "cent" not in t and "mille" not in t:
            base = _UNITS[t]
            push(base + _UNITS[toks[i + 1]]); i += 2; known = True; seen_known = True; continue
        if t in _UNITS:
            push(_UNITS[t]); i += 1; known = True; seen_known = True; continue
        i += 1

    if not seen_known:
        return None

    total, current = 0, 0
    for v in vals:
        if v in (1000000, 1000000000):
            total += (current or 1) * v
            current = 0
        elif v == 1000:
            total += (current or 1) * 1000
            current = 0
        elif v == 100:
            current = (current or 1) * 100
        else:
            current += v
    return total + current


# ---------------------------------------------------------------- dates
_MONTH_ALIASES = {
    1: ["janvier", "janv"],
    2: ["février", "fevrier", "fev"],
    3: ["mars"],
    4: ["avril", "avr"],
    5: ["mai"],
    6: ["juin"],
    7: ["juillet", "juil"],
    8: ["août", "aout"],
    9: ["septembre", "sept"],
    10: ["octobre", "oct"],
    11: ["novembre", "nov"],
    12: ["décembre", "decembre", "dec"],
}
_MONTHS_SORTED = sorted(
    ((v.lower(), m) for m, vs in _MONTH_ALIASES.items() for v in vs),
    key=lambda pair: len(pair[0]), reverse=True,
)
_DAYS_WEEK = {"lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"}
_NUM_TOKENS = set(_UNITS)


def _month_index_from(text):
    """Retourne (index_mois, libellé_rencontré) si un mois est présent dans le texte."""
    low = str(text or "").lower()
    for label, m in _MONTHS_SORTED:
        if label in low:
            return m, label
    return None, None


def _scan_numbers(words):
    """Parcourt une liste de tokens et produit les nombres (digits ou toutes lettres).

    Consomme les plus longues expressions numériques possibles : 'deux mille vingt-trois'
    -> 2023 (et pas seulement 1000). Génère (valeur, index_de_fin)."""
    i, n = 0, len(words)
    while i < n:
        t = words[i]
        if t.isdigit():
            yield int(t), i + 1
            i += 1
            continue
        if t in _NUM_TOKENS:
            best, best_end = None, i
            for j in range(i + 1, n + 1):
                w = words_to_int(" ".join(words[i:j]))
                if w is not None:
                    best, best_end = w, j
                # une expression partielle non valide casse la longueur : on garde le meilleur
            if best is not None:
                yield best, best_end
                i = best_end
                continue
        i += 1


def _extract_number_around(text, before=None, after=None):
    """Extrait jour (avant le mois) et année (après le mois), en chiffres ou toutes lettres."""
    day, year = None, None
    # jour avant le mois
    if before:
        b = re.sub(r"-", " ", before.lower())
        toks = [t for t in _words(b) if t not in _DAYS_WEEK and t != "le" and t != "vers" and t != "au" and t != "du" and t != "de"]
        found = list(_scan_numbers(toks))
        if found:
            for val, _end in reversed(found):
                if 1 <= val <= 31:
                    day = val
                    break
    # année après le mois
    if after:
        a = re.sub(r"-", " ", after.lower())
        toks = [t for t in _words(a) if t != "a" and t != "v" and t != "vers" and t != "de" and t != "du"]
        for val, _end in _scan_numbers(toks):
            if 100 <= val <= 9999 or 1 <= val <= 99:
                if val <= 99:
                    val = 2000 + val if val <= 69 else 1900 + val
                if 1900 <= val <= 2100:
                    year = val
                break
    return day, year


def parse_any_date(value):
    """Détecte une date dans presque tous les formats.

    Formats supportés : ISO (2023-07-15), SAE (15/07/2023, 15-07-2023, 15.07.2023),
    2023/07/15, jours+mois en toutes lettres (« quinze juillet deux mille vingt-trois »),
    « le 15 juillet 2023 », sans année (année courante), numériques sériels Excel.
    Retourne 'YYYY-MM-DD' ou None.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    v = str(value).strip()
    if not v:
        return None

    # datetime ISO -> date
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", v)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date().isoformat()
        except ValueError:
            pass

    # série Excel (nombre pur plausible)
    if re.match(r"^\d{4,6}([.,]\d+)?$", v.replace(" ", "")):
        try:
            serial = int(float(v.replace(",", ".").replace(" ", "")))
            if 20000 <= serial <= 70000:
                return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()
        except (OverflowError, ValueError):
            pass

    # traite la date honoraire (retire heure : "15/07/2023 10:30")
    v_clean = re.sub(r"\s+\d{1,2}[:h]\d{2}.*$", "", v)

    # Mois en toutes lettres
    mi, _tok = _month_index_from(v_clean)
    if mi:
        parts = re.split(r"(?i)\b" + re.escape(_tok) + r"\b", v_clean, maxsplit=1)
        day, year = _extract_number_around(v_clean, before=parts[0] if len(parts) > 0 else "",
                                           after=parts[1] if len(parts) > 1 else "")
        if year is None:
            year = date.today().year
        if day is None:
            day = 1
        try:
            return date(year, mi, day).isoformat()
        except ValueError:
            return None

    # formats séparés par / - . ou espace avec année 2/4 chiffres
    base = re.split(r"\s+", v_clean.strip())[0] if any(ch in v_clean for ch in "/-.") else v_clean
    for sep in ("/", "-", "."):
        if sep in base:
            p = [x for x in base.split(sep) if x != ""]
            if len(p) == 3:
                a, b, c = p
                if not (a.isdigit() and b.isdigit() and c.isdigit()):
                    continue
                if len(a) == 4:  # YYYY-MM-DD / YYYY/MM/DD
                    y, mo, da = int(a), int(b), int(c)
                else:  # JJ/MM/AAAA
                    da, mo, y = int(a), int(b), int(c)
                    if y < 100:
                        y = 2000 + y if y <= 69 else 1900 + y
                try:
                    return date(y, mo, da).isoformat()
                except ValueError:
                    return None
            if len(p) == 2 and p[0].isdigit() and p[1].isdigit():  # JJ/MM
                da, mo = int(p[0]), int(p[1])
                try:
                    return date(date.today().year, mo, da).isoformat()
                except ValueError:
                    return None
    return None


# ---------------------------------------------------------------- classification de cellules
_MARQUES = {
    "toyota", "peugeot", "renault", "citroen", "mercedes", "bmw", "audi", "nissan",
    "hyundai", "kia", "ford", "mitsubishi", "suzuki", "honda", "volkswagen", "vw",
    "opel", "fiat", "mazda", "hino", "isuzu", "iveco", "man", "scania", "daf",
    "landrover", "range", "kia", "chevrolet", "jeep", "dodge", "volvo", "seat",
    "skoda", "tata", "mahindra", "higer", "yutong", "kinglong", "buick", "acura",
    "infiniti", "lexus", "mitsibishi", "lotus", "maserati", "porsche", "subaru",
    "yamaha", "bajaj", "tvs", "hero", "hao jui", "aprilia", "ktm", "gac",
}
_MARQUES_NORM = None


def _is_marque(v):
    global _MARQUES_NORM
    if _MARQUES_NORM is None:
        _MARQUES_NORM = {_norm(m) for m in _MARQUES}
    n = _norm(v)
    return n in _MARQUES_NORM or any(n.startswith(_norm(m)) for m in ("toyota", "peugeot", "mercedes", "renault", "citroen") if n.startswith(_norm(m)))


_TYPES_VEHICULE = {"utilitaire", "berline", "camion", "fourgon", "suv", "pickup", "pick-up",
                   "motocyclette", "moto", "bus", "car", "mini", "trailer", "semi", "benne",
                   "citern e", "citern", "fourgonette", "van", "sedan", "coaster"}
_FUELS = {"diesel", "essence", "essencesansplomb", "electricite", "electrique", "gazole",
          "hybride", "gpl", "gaz", "super", "petrole", "ethanol"}
_STATUTS = {"enservice", "en service", "horsservice", "hors service", "enpanne", "en panne",
            "enrevision", "en revision", "envente", "a vendre", "vendu", "attribue", "disponible"}
_RESULTATS = {"conforme", "nonconforme", "refuse", "valide", "invalide", "ajourne", "favorable",
              "defavorable", "ok", "bon", "defectueux", "enattente", "en cours"}
_HUILES = {"huile", "huilemoteur", "10w40", "15w40", "5w30", "20w50", "mobil", "total", "castrol",
           "shell", "esso"}


def classify_value(value):
    """Qualifie une valeur : plate, marque, date, int, float, bool, phone, email, etc."""
    v = str(value or "").strip()
    if not v:
        return {"type": "blank", "confidence": 0.0}
    vv = v.upper()
    # plaque d'immatriculation (CE 291 OD, LT-345-AB, 1234 TU...)
    if re.match(r"^[A-Z]{1,4}[\s-]?\d{1,5}[\s-]?[A-Z]{1,3}$", vv) and any(ch.isdigit() for ch in vv):
        return {"type": "plate", "confidence": 0.95}
    if re.match(r"^\d{2,6}[\s-][A-Z]{1,3}$", vv):
        return {"type": "plate", "confidence": 0.9}
    # email
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
        return {"type": "email", "confidence": 1.0}
    # téléphone camerounais / international
    digits = re.sub(r"[^\d]", "", v)
    if re.match(r"^(?:\+237|237)?[256789]\d{7,8}$", v.replace(" ", "").replace("-", "")) and 8 <= len(digits) <= 12:
        return {"type": "phone", "confidence": 0.9}
    # matricule / identifiant (M-001, EMP 2024, AG-12)
    if re.match(r"^[A-Za-z]{1,5}[-/ ]?\d{2,6}$", v) and re.search(r"\d", v):
        return {"type": "matricule", "confidence": 0.75}
    # code document / référence alphanumérique (CG-2023-0147, P-123456, 24A/2023)
    if len(v) <= 24 and re.match(r"^[A-Za-z]{1,12}[-/]?\d{1,12}([-/][A-Za-z0-9-]*)?$", v) \
            and re.search(r"[A-Za-z]", v) and re.search(r"\d", v):
        return {"type": "code", "confidence": 0.6}
    # booléens
    n = _norm(v)
    if n in ("oui", "non", "yes", "no", "true", "false", "vrai", "faux", "ok", "1", "0"):
        return {"type": "bool", "confidence": 0.9}
    # nombre
    num = v.replace("\u00a0", " ").replace(" ", "")
    num_clean = num.replace(",", ".")
    if re.match(r"^-?\d+$", num):
        iv = int(num)
        if 1970 <= iv <= 2100:
            return {"type": "year", "confidence": 0.88}
        if 500 <= iv <= 2000000:
            return {"type": "km", "confidence": 0.7}
        if 1 <= iv <= 500:
            return {"type": "cv", "confidence": 0.6}
        return {"type": "int", "confidence": 0.7}
    if re.match(r"^-?\d+[.,]\d+$", num_clean):
        try:
            fv = float(num_clean)
            if 100 <= fv <= 200000000:
                return {"type": "amount", "confidence": 0.7}
            return {"type": "float", "confidence": 0.6}
        except ValueError:
            pass
    # date en toutes lettres ou formats
    if parse_any_date(v) is not None:
        return {"type": "date", "confidence": 0.9}
    # marque
    if _is_marque(v):
        return {"type": "marque", "confidence": 0.9}
    n2 = _norm(v)
    if n2 in {_norm(t) for t in _TYPES_VEHICULE}:
        return {"type": "vehicle_type", "confidence": 0.8}
    if n2 in {_norm(f) for f in _FUELS}:
        return {"type": "fuel", "confidence": 0.85}
    if n2 in {_norm(s) for s in _STATUTS}:
        return {"type": "status", "confidence": 0.85}
    if n2 in {_norm(r) for r in _RESULTATS}:
        return {"type": "resultat", "confidence": 0.8}
    if any(_norm(h) in n2 for h in _HUILES):
        return {"type": "huile", "confidence": 0.7}
    if any(w in n2 for w in ("fcfa", "frs", "franc")):
        return {"type": "amount", "confidence": 0.85}
    return {"type": "text", "confidence": 0.5}


def column_types(values, limit=40):
    """Profil de types d'une colonne : dict type -> ratio sur un échantillon."""
    counts = {}
    n = 0
    for val in values:
        if val is None or str(val).strip() == "":
            continue
        n += 1
        t = classify_value(val)["type"]
        counts[t] = counts.get(t, 0) + 1
        if n >= limit:
            break
    if n == 0:
        return {}
    return {t: c / n for t, c in counts.items()}


# ---------------------------------------------------------------- scoring colonnes / champs
def match_header(header, synonyms):
    """Score de similarité 0..1 entre un en-tête et un ensemble de synonymes (norm).

    Les en-têtes très courts (1-2 caractères, ex: 'D') sont trop ambigus pour une
    correspondance par sous-chaîne : on les compare uniquement par similarité exacte/floue.
    """
    h = _norm(header)
    if not h:
        return 0.0
    for s in synonyms:
        s = _norm(s)
        if s == h:
            return 1.0
        if min(len(h), len(s)) >= 3 and (s in h or h in s):
            return 0.9
        # similarité floue
        r = SequenceMatcher(None, h, s).ratio()
        if r >= 0.8:
            return max(0.0, r)
    return 0.0


def field_content_score(field, types):
    """Score 0..1 de correspondance du contenu d'une colonne avec un champ."""
    score = 0.0
    if not types:
        return 0.0
    def get(*keys):
        return max((types.get(k, 0.0) for k in keys), default=0.0)

    if field in ("immatriculation", "plaque"):
        score = get("plate")
    elif field == "marque":
        score = get("marque")
    elif field == "annee":
        score = max(get("year"), get("int") * 0.7)
    elif field == "kilometrage" or field in ("km", "prochaine_km"):
        score = max(get("km"), get("int") * 0.5)
    elif field == "cv":
        score = max(get("cv"), get("int") * 0.5)
    elif field == "cout" or field == "couts":
        score = get("amount")
    elif field == "type":
        score = max(get("vehicle_type"), get("text") * 0.25)
    elif field == "carburant":
        score = get("fuel")
    elif field == "statut":
        score = get("status")
    elif field == "resultat":
        score = get("resultat")
    elif field in ("vignette_exp", "assurance_exp", "ctrl_tech_exp", "carte_grise_exp",
                   "permis_exp", "cni_exp", "date", "date_due"):
        score = get("date")
    elif field == "telephone":
        score = get("phone")
    elif field == "email":
        score = get("email")
    elif field == "matricule":
        score = get("matricule")
    elif field == "huile":
        score = max(get("huile"), get("text") * 0.2)
    elif field in ("nom", "prenom", "conducteur", "garage", "affectation", "direction"):
        score = get("text") * 0.5 + max(get("marque"), 0.0) * 0.0
    elif field in ("quantite", "litres"):
        score = max(get("float"), get("int") * 0.4)
    elif field == "filtre":
        score = get("bool")
    elif field in ("notes", "observations", "remarques", "description"):
        score = get("text") * 0.3
    elif field == "numero":
        score = max(get("code") * 0.7, get("matricule") * 0.6, get("int") * 0.4, get("text") * 0.2)
    elif field == "permis":
        score = get("int") * 0.3
    return max(0.0, min(1.0, score))


def column_best_field(header, types, fields, header_strength=0.6, content_strength=0.4):
    """Trouve le meilleur champ d'un ensemble de champs pour une colonne (en-tête + contenu)."""
    best_field, best_score = None, 0.0
    for field, synonyms in fields.items():
        hs = match_header(header, synonyms)
        cs = field_content_score(field, types)
        score = hs * header_strength + cs * content_strength
        if score > best_score:
            best_score, best_field = score, field
    return best_field, best_score


def map_columns(headers, rows, fields, header_strength=0.6, content_strength=0.4):
    """Cartographie automatique en-têtes->champs en combinant similarité d'en-tête et contenu.

    headers : liste des en-têtes. rows : liste de lignes (list). fields : {champ: {synonymes}}.
    Retourne {champ: index_colonne} (chaque colonne n'est affectée qu'une fois).
    """
    ncols = len(headers)
    col_values = [[] for _ in range(ncols)]
    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        for ci in range(min(ncols, len(row))):
            if row[ci] is not None and str(row[ci]).strip():
                col_values[ci].append(row[ci])

    # score par (champ, colonne)
    cands = {}
    col_types = []
    for ci in range(ncols):
        types = column_types(col_values[ci])
        col_types.append(types)
        fld, sc = column_best_field(headers[ci], types, fields, header_strength, content_strength)
        cands[ci] = (fld, sc)

    used_cols = set()
    result = {}
    for fld in sorted(fields, key=lambda f: -max(
            (cands[ci][1] for ci in range(ncols) if cands[ci][0] == f), default=0.0)):
        best_ci, best_sc = None, 0.35
        for ci in range(ncols):
            if ci in used_cols:
                continue
            if cands[ci][0] != fld:
                continue
            if cands[ci][1] > best_sc:
                best_ci, best_sc = ci, cands[ci][1]
        if best_ci is not None:
            result[fld] = best_ci
            used_cols.add(best_ci)

    # heuristique conducteurs : en-têtes génériques -> colonnes texte restantes
    # affectées à "nom" puis "prénom" dans l'ordre (convention Nom, Prénom)
    if "nom" in fields and "prenom" in fields:
        def _dominant(types):
            return max(types.items(), key=lambda kv: kv[1])[0] if types else "text"
        free_text = [ci for ci in range(ncols)
                     if ci not in used_cols and _dominant(col_types[ci]) == "text"]
        if "nom" not in result and free_text:
            result["nom"] = free_text.pop(0)
            used_cols.add(result["nom"])
        if "prenom" not in result and free_text and _dominant(col_types[free_text[0]]) == "text":
            result["prenom"] = free_text.pop(0)
            used_cols.add(result["prenom"])
    return result


# ---------------------------------------------------------------- détection d'entité
KIND_WEIGHTS = {
    "vehicles": {
        "immatriculation": 3.0, "marque": 2.0, "modele": 1.5, "annee": 1.0,
        "carburant": 1.0, "kilometrage": 1.5, "statut": 0.8, "affectation": 0.8,
        "direction": 0.8, "type": 0.8, "vignette_exp": 1.0, "assurance_exp": 1.0,
        "ctrl_tech_exp": 1.0, "carte_grise": 0.8, "carte_grise_exp": 1.0, "cv": 0.8,
        "num_chassis": 0.6, "num_moteur": 0.6,
    },
    "drivers": {
        "nom": 3.0, "prenom": 2.5, "matricule": 1.0, "telephone": 1.0, "email": 1.0,
        "permis": 2.0, "permis_exp": 1.0, "cni_exp": 1.0,
    },
    "controls": {
        "immatriculation": 2.0, "date": 2.0, "type": 1.0, "resultat": 1.5,
        "conducteur": 1.0, "notes": 0.5,
    },
    "maintenance": {
        "immatriculation": 2.0, "date": 2.0, "cout": 1.5, "type": 1.5, "garage": 1.0,
        "notes": 0.5,
    },
    "vidanges": {
        "immatriculation": 2.0, "date": 2.0, "km": 2.0, "huile": 1.0, "quantite": 1.0,
        "filtre": 0.8, "cout": 1.0, "garage": 0.8, "prochaine_km": 1.5, "notes": 0.5,
    },
    "vignettes": {
        "immatriculation": 3.0, "date": 3.5, "notes": 0.5,
    },
    "controles_tech": {
        "immatriculation": 2.0, "date": 3.0, "resultat": 1.5, "notes": 0.5,
    },
    "cartes_grise": {
        "immatriculation": 2.0, "numero": 2.0, "date": 2.5, "notes": 0.5,
    },
    "permis": {
        "nom": 3.0, "prenom": 2.5, "numero": 2.5, "date": 1.5, "notes": 0.5,
    },
    "cni": {
        "nom": 3.0, "prenom": 2.5, "numero": 1.5, "date": 1.5, "notes": 0.5,
    },
}


def detect_kind(headers, rows, all_fields, h_strength=0.55, c_strength=0.45):
    """Détecte l'entité du fichier à partir des en-têtes ET du contenu.

    all_fields : {kind: {champ: {synonyms}}}. Petit masseur : retourne (kind, map_columns) pour
    les champs du kind gagnant, ou (None, None) si indéterminé.
    """
    ncols = len(headers)
    col_values = [[] for _ in range(ncols)]
    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        for ci in range(min(ncols, len(row))):
            if row[ci] is not None and str(row[ci]).strip():
                col_values[ci].append(row[ci])

    # union de tous les champs
    union = {}
    for kind, fields in all_fields.items():
        for field, syn in fields.items():
            union.setdefault(field, syn)
    col_types = [column_types(col_values[ci]) for ci in range(ncols)]

    scores = {}
    for kind, fields in all_fields.items():
        score = 0.0
        for ci in range(ncols):
            best_f, best_sc = None, 0.0
            for field, syn in fields.items():
                sc = match_header(headers[ci], syn) * h_strength \
                    + field_content_score(field, col_types[ci]) * c_strength
                if sc > best_sc:
                    best_sc, best_f = sc, field
            if best_f is not None and best_sc > 0:
                score += KIND_WEIGHTS.get(kind, {}).get(best_f, 1.0) * best_sc
        scores[kind] = score

    if not scores:
        return None, None
    ranking = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    winner, wscore = ranking[0]
    runner_up = ranking[1][1] if len(ranking) > 1 else 0.0
    # un gagnant crédible : score minimum ET avance nette sur le second (éviter les non-diagnostics)
    if wscore < 0.8 or (runner_up > 0 and wscore - runner_up < 0.5):
        return None, None

    # une entité « véhicules » qui n'aurait ni immatriculation ni marque est peu probable
    fmap = map_columns(headers, rows, all_fields[winner], h_strength, c_strength)
    return winner, fmap