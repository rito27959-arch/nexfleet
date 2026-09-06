# -*- coding: utf-8 -*-
"""NexFleet — API REST de gestion de parc automobile."""

import io
import json
import os
import re
import sqlite3
import sys
import tempfile
from datetime import date, datetime, timedelta
from math import ceil

from flask import Flask, Response, g, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assistant
import budget as budget_module
import imp_exp
import io_xlsx
import notify
import pdf as pdfgen
from auth import admin_required, create_token, hash_password, token_required, verify_password
from db import DB_PATH, UPLOAD_DIR, get_db, get_setting, init_db, now, row_to_dict, set_setting

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# ---------------------------------------------------------------- application
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

init_db()
notify.start_scheduler()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def DATE_OK(d):
    if not d:
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(d)):
        return False
    try:
        datetime.strptime(str(d), "%Y-%m-%d")
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- helpers
def err(message, code=400):
    return jsonify({"error": message}), code


def parse_items(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def today():
    return date.today().isoformat()


def log_action(action, entity=None, entity_id=None, details=None):
    """Enregistre une action dans le journal d'activité (audit)."""
    db = get_db()
    db.execute(
        "INSERT INTO audit_log (user_id, username, action, entity, entity_id, details, created_at) VALUES (?,?,?,?,?,?,?)",
        (getattr(request, "user_id", None),
         getattr(request, "user_name", None) or (request.get_json(silent=True) or {}).get("username", ""),
         action, entity, entity_id,
         json.dumps(details, ensure_ascii=False) if details else None, now()))
    db.commit()
    db.close()


def days_left(iso):
    if not iso:
        return None
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
        return (d - date.today()).days
    except (ValueError, TypeError):
        return None


def vehicle_alerts(vehicle):
    """Liste des alertes d'échéance pour un véhicule (assurance, vignette, CT)."""
    try:
        threshold = max(1, min(365, int(get_setting("alert_threshold", "30"))))
    except (ValueError, TypeError):
        threshold = 30
    alerts = []
    for key, label in (("assurance_exp", "Assurance"), ("vignette_exp", "Vignette"),
                       ("ctrl_tech_exp", "Contrôle technique"), ("carte_grise_exp", "Carte grise")):
        dl = days_left(vehicle.get(key))
        if dl is not None and dl <= threshold:
            if dl < 0:
                alerts.append({"type": key, "label": label, "days": dl, "level": "danger",
                               "msg": f"{label} expirée depuis {-dl} jour(s)"})
            else:
                alerts.append({"type": key, "label": label, "days": dl, "level": "warning",
                               "msg": f"{label} expire dans {dl} jour(s)"})
    return alerts


VIDANGE_ALERT_KM = 500


def vidange_km_alert(db, vehicle):
    """Alerte kilométrique vidange : prochaine vidange atteinte ou dans
    moins de ``VIDANGE_ALERT_KM`` kilomètres (par défaut 500)."""
    try:
        interval = max(500, int(get_setting("forecast_km", "10000")))
    except (ValueError, TypeError):
        interval = 10000
    try:
        alert_km = max(100, min(10000, int(get_setting("vidange_alert_km", str(VIDANGE_ALERT_KM)))))
    except (ValueError, TypeError):
        alert_km = VIDANGE_ALERT_KM
    alerts = []
    vg = db.execute(
        "SELECT * FROM vidanges WHERE vehicle_id=? ORDER BY date DESC, id DESC LIMIT 1",
        (vehicle["id"],)).fetchone()
    if vg is None:
        return alerts
    vg = dict(vg)
    km_due = vg.get("prochaine_km") or ((vg.get("km") or 0) + interval)
    km_now = vehicle.get("kilometrage") or 0
    km_left = km_due - km_now
    if km_left <= 0:
        alerts.append({"type": "vidange", "label": "Vidange", "days": km_left, "level": "danger",
                       "msg": f"Vidange à effectuer — dépassée de {-km_left} km"})
    elif km_left <= alert_km:
        alerts.append({"type": "vidange", "label": "Vidange", "days": km_left, "level": "warning",
                       "msg": f"Vidange à prévoir dans {km_left} km"})
    return alerts


def all_alerts():
    """Toutes les alertes d'échéance du parc (échéances + vidange + permis), triées par urgence."""
    db = get_db()
    rows = [dict(r) for r in db.execute("SELECT * FROM vehicles").fetchall()]
    alerts = []
    for v in rows:
        base = {"vehicle": f"{v['marque']} {v['modele']}", "immatriculation": v["immatriculation"]}
        for a in vehicle_alerts(v):
            alerts.append({**a, **base})
        for a in vidange_km_alert(db, v):
            alerts.append({**a, **base})
    try:
        threshold = max(1, min(365, int(get_setting("alert_threshold", "30"))))
    except (ValueError, TypeError):
        threshold = 30
    for d in [dict(r) for r in db.execute("SELECT * FROM drivers").fetchall()]:
        if d.get("permis_exp"):
            dl = days_left(d["permis_exp"])
            if dl is not None and dl <= threshold:
                level = "danger" if dl < 0 else "warning"
                msg = f"Permis expiré depuis {-dl} jour(s)" if dl < 0 else f"Permis expire dans {dl} jour(s)"
                alerts.append({"type": "permis", "label": "Permis", "days": dl, "level": level, "msg": msg,
                               "vehicle": f"{d['prenom']} {d['nom']}", "immatriculation": d.get("permis") or ""})
        if d.get("cni_exp"):
            dl = days_left(d["cni_exp"])
            if dl is not None and dl <= threshold:
                level = "danger" if dl < 0 else "warning"
                msg = f"CNI expirée depuis {-dl} jour(s)" if dl < 0 else f"CNI expire dans {dl} jour(s)"
                alerts.append({"type": "cni", "label": "Carte identité", "days": dl, "level": level, "msg": msg,
                               "vehicle": f"{d['prenom']} {d['nom']}", "immatriculation": d.get("permis") or ""})
    db.close()
    alerts.sort(key=lambda a: (a.get("days", 0), a.get("type", "")))
    return alerts


def vehicle_history(db, vid):
    """Historique complet d'un véhicule (création, contrôles, maintenance, vidanges,
    relevés kilométriques, pneus, documents) avec coûts, trié chronologiquement."""
    events = []
    veh = db.execute("SELECT * FROM vehicles WHERE id=?", (vid,)).fetchone()
    if veh is None:
        return events
    veh = dict(veh)
    if veh.get("created_at"):
        events.append({
            "date": str(veh["created_at"])[:10], "sort": str(veh["created_at"]),
            "kind": "creation", "label": "Ajout du véhicule",
            "detail": f"{veh['marque']} {veh['modele']} · {veh['immatriculation']}",
            "cost": 0.0,
        })
    for r in db.execute(
            """SELECT c.*, d.nom AS d_nom, d.prenom AS d_prenom
               FROM controls c LEFT JOIN drivers d ON d.id = c.driver_id
               WHERE c.vehicle_id=? ORDER BY c.date, c.id""", (vid,)).fetchall():
        c = dict(r)
        detail = c.get("resultat") or ""
        if c.get("d_nom"):
            detail += f" — {c['d_prenom']} {c['d_nom']}"
        if c.get("notes"):
            detail += f" · {c['notes']}"
        events.append({"date": c["date"], "sort": c["date"], "kind": "control",
                       "label": c.get("type") or "Contrôle", "detail": detail, "cost": 0.0})
    for r in db.execute(
            "SELECT * FROM maintenance WHERE vehicle_id=? ORDER BY date, id", (vid,)).fetchall():
        m = dict(r)
        detail = m.get("notes") or ""
        if m.get("garage"):
            detail += (f" — {m['garage']}" if detail else m["garage"])
        events.append({"date": m["date"], "sort": m["date"], "kind": "maintenance",
                       "label": m.get("type") or "Maintenance", "detail": detail,
                       "cost": float(m.get("cout") or 0)})
    for r in db.execute(
            "SELECT * FROM vidanges WHERE vehicle_id=? ORDER BY date, id", (vid,)).fetchall():
        vg = dict(r)
        detail = f"{vg.get('huile') or 'Huile'} · {vg.get('km') or 0} km"
        parts = []
        if vg.get("filtre_huile") or vg.get("filtre"):
            parts.append("filtre à huile")
        if vg.get("filtre_gasoil"):
            parts.append("filtre à gazoil")
        if vg.get("huile_transmission"):
            parts.append("huile transmission")
        if vg.get("liquide_refroidissement"):
            parts.append("liquide refroidissement")
        if vg.get("liquide_laveglace"):
            parts.append("lave-glace")
        if parts:
            detail += " · " + ", ".join(parts)
        if vg.get("garage"):
            detail += f" — {vg['garage']}"
        if vg.get("notes"):
            detail += f" · {vg['notes']}"
        events.append({"date": vg["date"], "sort": vg["date"], "kind": "vidange",
                       "label": "Vidange", "detail": detail,
                       "cost": float(vg.get("cout") or 0)})
    for r in db.execute(
            "SELECT * FROM odometer WHERE vehicle_id=? ORDER BY date, id", (vid,)).fetchall():
        o = dict(r)
        detail = f"{o['kilometres']} km"
        if o.get("note"):
            detail += f" · {o['note']}"
        events.append({"date": o["date"], "sort": o["date"], "kind": "odometer",
                       "label": "Relevé kilométrique", "detail": detail, "cost": 0.0})
    for r in db.execute("SELECT * FROM tires WHERE vehicle_id=?", (vid,)).fetchall():
        t = dict(r)
        detail = f"{t.get('marque') or 'Pneu'} {t.get('taille') or ''}".strip() or "Montage"
        if t.get("etat"):
            detail += f" · {t['etat']}"
        events.append({"date": t.get("date_montage") or str(t.get("created_at") or "")[:10],
                       "sort": t.get("date_montage") or str(t.get("created_at") or ""),
                       "kind": "tire", "label": f"Pneu {t.get('position')}",
                       "detail": detail, "cost": 0.0})
    for r in db.execute(
            "SELECT * FROM documents WHERE vehicle_id=? ORDER BY created_at, id", (vid,)).fetchall():
        d = dict(r)
        events.append({"date": str(d.get("created_at") or "")[:10],
                       "sort": str(d.get("created_at") or ""), "kind": "document",
                       "label": "Document ajouté",
                       "detail": d.get("label") or d.get("filename") or "", "cost": 0.0})
    events.sort(key=lambda ev: ev.get("sort") or ev.get("date") or "")
    return events


# ---------------------------------------------------------------- auth
@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "NexFleet API", "time": now()})


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not (4 <= len(username) <= 32):
        return err("Nom d'utilisateur : 4 à 32 caractères.")
    if not EMAIL_RE.match(email):
        return err("Adresse e-mail invalide.")
    if len(password) < 8:
        return err("Mot de passe : 8 caractères minimum.")
    if not any(c.isdigit() for c in password):
        return err("Le mot de passe doit contenir au moins un chiffre.")

    db = get_db()
    try:
        count = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        role = "admin" if count == 0 else "user"
        cur = db.execute(
            "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?,?,?,?,?)",
            (username, email, hash_password(password), role, now()),
        )
        db.commit()
        uid = cur.lastrowid
    except Exception:
        db.rollback()
        return err("Nom d'utilisateur ou e-mail déjà utilisé.", 409)
    finally:
        db.close()

    log_action("register", "user", uid, {"username": username})
    return jsonify({"token": create_token(uid, role, username),
                    "user": {"id": uid, "username": username, "email": email, "role": role}}), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    ident = (data.get("username") or data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    db = get_db()
    row = db.execute(
        "SELECT * FROM users WHERE LOWER(username)=? OR LOWER(email)=?", (ident, ident)
    ).fetchone()
    db.close()
    if row is None or not verify_password(password, row["password_hash"]):
        return err("Identifiants incorrects.", 401)
    log_action("login", "user", row["id"], {"username": row["username"]})
    return jsonify({"token": create_token(row["id"], row["role"], row["username"]),
                    "user": {"id": row["id"], "username": row["username"],
                             "email": row["email"], "role": row["role"]}})


@app.get("/api/auth/me")
@token_required
def me():
    db = get_db()
    row = db.execute("SELECT id, username, email, role, created_at FROM users WHERE id=?",
                     (request.user_id,)).fetchone()
    db.close()
    return jsonify({"user": row_to_dict(row)})


@app.put("/api/auth/password")
@token_required
def change_password():
    data = request.get_json(silent=True) or {}
    old = data.get("old_password") or ""
    new = data.get("new_password") or ""
    if len(new) < 8 or not any(c.isdigit() for c in new):
        return err("Nouveau mot de passe : 8 caractères minimum avec un chiffre.")
    db = get_db()
    row = db.execute("SELECT password_hash FROM users WHERE id=?", (request.user_id,)).fetchone()
    if row is None or not verify_password(old, row["password_hash"]):
        db.close()
        return err("Ancien mot de passe incorrect.", 401)
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new), request.user_id))
    db.commit()
    db.close()
    return jsonify({"ok": True, "message": "Mot de passe mis à jour."})


@app.get("/api/users")
@token_required
@admin_required
def list_users():
    db = get_db()
    rows = db.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id").fetchall()
    db.close()
    return jsonify({"users": [row_to_dict(r) for r in rows]})


@app.post("/api/users")
@token_required
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = "admin" if data.get("role") == "admin" else "user"
    if not (4 <= len(username) <= 32):
        return err("Nom d'utilisateur : 4 à 32 caractères.")
    if not EMAIL_RE.match(email):
        return err("Adresse e-mail invalide.")
    if len(password) < 8 or not any(c.isdigit() for c in password):
        return err("Mot de passe : 8 caractères minimum avec un chiffre.")
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                   (username, email, hash_password(password), role, now()))
        db.commit()
    except Exception:
        db.rollback()
        return err("Nom d'utilisateur ou e-mail déjà utilisé.", 409)
    finally:
        db.close()
    log_action("create", "user", None, {"username": username, "role": role})
    return jsonify({"ok": True, "message": "Utilisateur créé."}), 201


@app.put("/api/users/<int:uid>/role")
@token_required
@admin_required
def set_user_role(uid):
    role = "admin" if (request.get_json(silent=True) or {}).get("role") == "admin" else "user"
    db = get_db()
    row = db.execute("SELECT id, username, role FROM users WHERE id=?", (uid,)).fetchone()
    if row is None:
        db.close()
        return err("Utilisateur introuvable.", 404)
    if role == row["role"]:
        db.close()
        return jsonify({"ok": True, "message": "Aucun changement de rôle."})
    if row["id"] == request.user_id:
        db.close()
        return err("Impossible de modifier votre propre rôle.", 400)
    if row["role"] == "admin" and role == "user":
        admins = db.execute("SELECT COUNT(*) AS n FROM users WHERE role='admin'").fetchone()["n"]
        if admins <= 1:
            db.close()
            return err("Impossible de rétrograder le dernier administrateur.", 400)
    db.execute("UPDATE users SET role=? WHERE id=?", (role, uid))
    db.commit()
    db.close()
    log_action("role", "user", uid, {"username": row["username"], "role": role})
    return jsonify({"ok": True, "message": f"Rôle de {row['username']} mis à jour ({role})."})


@app.put("/api/users/<int:uid>/password")
@token_required
@admin_required
def reset_user_password(uid):
    password = (request.get_json(silent=True) or {}).get("password") or ""
    if len(password) < 8 or not any(c.isdigit() for c in password):
        return err("Mot de passe : 8 caractères minimum avec un chiffre.")
    db = get_db()
    row = db.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
    if row is None:
        db.close()
        return err("Utilisateur introuvable.", 404)
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password), uid))
    db.commit()
    db.close()
    log_action("reset_password", "user", uid, {"username": row["username"]})
    return jsonify({"ok": True, "message": f"Mot de passe de {row['username']} réinitialisé."})


@app.delete("/api/users/<int:uid>")
@token_required
@admin_required
def delete_user(uid):
    db = get_db()
    row = db.execute("SELECT id, username, role FROM users WHERE id=?", (uid,)).fetchone()
    if row is None:
        db.close()
        return err("Utilisateur introuvable.", 404)
    if row["id"] == request.user_id:
        db.close()
        return err("Impossible de supprimer votre propre compte.", 400)
    if row["role"] == "admin":
        admins = db.execute("SELECT COUNT(*) AS n FROM users WHERE role='admin'").fetchone()["n"]
        if admins <= 1:
            db.close()
            return err("Impossible de supprimer le dernier administrateur.", 400)
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    db.close()
    log_action("delete", "user", uid, {"username": row["username"]})
    return jsonify({"ok": True, "message": "Utilisateur supprimé."})


# ---------------------------------------------------------------- stats
@app.get("/api/stats")
@token_required
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM vehicles").fetchone()["n"]
    en_service = db.execute("SELECT COUNT(*) AS n FROM vehicles WHERE statut LIKE 'En service'").fetchone()["n"]
    en_maintenance = db.execute("SELECT COUNT(*) AS n FROM vehicles WHERE statut LIKE '%maintenance%'").fetchone()["n"]
    en_panne = db.execute("SELECT COUNT(*) AS n FROM vehicles WHERE statut LIKE '%panne%'").fetchone()["n"]
    drivers = db.execute("SELECT COUNT(*) AS n FROM drivers").fetchone()["n"]
    controls_month = db.execute(
        "SELECT COUNT(*) AS n FROM controls WHERE substr(date,1,7)=?",
        (date.today().strftime("%Y-%m"),)).fetchone()["n"]
    controls_total = db.execute("SELECT COUNT(*) AS n FROM controls").fetchone()["n"]

    carburant = {r["carburant"] or "—": r["n"] for r in db.execute(
        "SELECT carburant, COUNT(*) AS n FROM vehicles GROUP BY carburant")}
    marques = {r["marque"] or "—": r["n"] for r in db.execute(
        "SELECT marque, COUNT(*) AS n FROM vehicles GROUP BY marque ORDER BY n DESC LIMIT 6")}

    last6 = []
    for i in range(5, -1, -1):
        m = (date.today().replace(day=1) - timedelta(days=i * 31)).strftime("%Y-%m")
        n = db.execute("SELECT COUNT(*) AS n FROM controls WHERE substr(date,1,7)=?", (m,)).fetchone()["n"]
        last6.append({"month": m, "count": n})

    rows = [dict(r) for r in db.execute("SELECT * FROM vehicles").fetchall()]
    alerts = all_alerts()

    maintenance_total = db.execute(
        "SELECT COALESCE(SUM(cout),0) AS n FROM maintenance").fetchone()["n"]
    costs_by_vehicle = [dict(r) for r in db.execute(
        """SELECT v.id, v.immatriculation, v.marque, v.modele, COALESCE(SUM(m.cout),0) AS total
           FROM vehicles v LEFT JOIN maintenance m ON m.vehicle_id = v.id
           GROUP BY v.id ORDER BY total DESC LIMIT 8""").fetchall()]
    cost_per_km = [dict(r) for r in db.execute(
        """SELECT v.immatriculation, v.marque, v.modele,
                  COALESCE(SUM(m.cout),0) AS total, MAX(v.kilometrage, 1) AS km
           FROM vehicles v LEFT JOIN maintenance m ON m.vehicle_id = v.id
           GROUP BY v.id ORDER BY total DESC""").fetchall()]
    for c in cost_per_km:
        c["value"] = round(c["total"] / max(c["km"], 1), 2)
    by_site = {r["affectation"] or "Non affecté": r["n"] for r in db.execute(
        "SELECT affectation, COUNT(*) AS n FROM vehicles GROUP BY affectation")}

    vidanges_total = db.execute(
        "SELECT COALESCE(SUM(cout),0) AS n FROM vidanges").fetchone()["n"]
    vidanges_count = db.execute("SELECT COUNT(*) AS n FROM vidanges").fetchone()["n"]
    vidanges_year = db.execute(
        "SELECT COUNT(*) AS n FROM vidanges WHERE substr(date,1,4)=?",
        (str(date.today().year),)).fetchone()["n"]
    db.close()

    return jsonify({
        "total": total, "en_service": en_service, "en_maintenance": en_maintenance,
        "en_panne": en_panne, "drivers": drivers, "controls_month": controls_month,
        "controls_total": controls_total, "carburant": carburant, "marques": marques,
        "controls_by_month": last6, "alerts": alerts[:12],
        "maintenance_total": float(maintenance_total),
        "costs_by_vehicle": costs_by_vehicle,
        "cost_per_km": cost_per_km,
        "by_site": by_site,
        "vidanges_total": float(vidanges_total),
        "vidanges_count": vidanges_count,
        "vidanges_year": vidanges_year,
    })


# ---------------------------------------------------------------- véhicules
def _safe_int(val):
    try:
        return int(val) if val not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None

def _safe_float(val):
    try:
        return float(val) if val not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None

def validate_vehicle(data):
    imm = (data.get("immatriculation") or "").strip().upper()
    marque = (data.get("marque") or "").strip()
    modele = (data.get("modele") or "").strip()
    if not imm or len(imm) < 5:
        return None, "Immatriculation invalide (5 caractères min)."
    if not marque or not modele:
        return None, "Marque et modèle requis."
    annee = data.get("annee") or None
    if annee:
        try:
            annee = int(annee)
            if not (1970 <= annee <= 2100):
                return None, "Année invalide."
        except (ValueError, TypeError):
            return None, "Année invalide."
    km = data.get("kilometrage") or 0
    try:
        km = int(km)
    except (ValueError, TypeError):
        km = 0
    for f in ("vignette_exp", "assurance_exp", "ctrl_tech_exp", "carte_grise_exp"):
        if data.get(f) and not DATE_OK(data[f]):
            return None, f"Date {f} invalide (format AAAA-MM-JJ)."
    return {
        "immatriculation": imm, "marque": marque, "modele": modele, "annee": annee,
        "type": data.get("type") or "Utilitaire", "carburant": data.get("carburant") or "Diesel",
        "kilometrage": max(km, 0), "vignette_exp": data.get("vignette_exp"),
        "assurance_exp": data.get("assurance_exp"), "ctrl_tech_exp": data.get("ctrl_tech_exp"),
        "statut": data.get("statut") or "En service",
        "direction": (data.get("direction") or "").strip() or None,
        "affectation": (data.get("affectation") or "").strip() or None,
        "num_chassis": (data.get("num_chassis") or "").strip() or None,
        "num_moteur": (data.get("num_moteur") or "").strip() or None,
        "cv": _safe_int(data.get("cv")),
        "carte_grise": (data.get("carte_grise") or "").strip() or None,
        "carte_grise_exp": data.get("carte_grise_exp"),
        "lat": _safe_float(data.get("lat")),
        "lng": _safe_float(data.get("lng")),
        "vignette_note": (data.get("vignette_note") or "").strip() or None,
        "ct_note": (data.get("ct_note") or "").strip() or None,
        "carte_grise_note": (data.get("carte_grise_note") or "").strip() or None,
    }, None


@app.get("/api/vehicles")
@token_required
def list_vehicles():
    search = (request.args.get("search") or "").strip()
    statut = (request.args.get("statut") or "").strip()
    carburant = (request.args.get("carburant") or "").strip()
    site = (request.args.get("site") or "").strip()
    sql = "SELECT * FROM vehicles WHERE 1=1"
    params = []
    if search:
        sql += " AND (immatriculation LIKE ? OR marque LIKE ? OR modele LIKE ? OR affectation LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like, like]
    if statut:
        sql += " AND statut LIKE ?"
        params.append(f"%{statut}%")
    if carburant:
        sql += " AND carburant = ?"
        params.append(carburant)
    if site:
        sql += " AND affectation = ?"
        params.append(site)
    sql += " ORDER BY created_at DESC, id DESC"
    db = get_db()
    rows = db.execute(sql, params).fetchall()
    out = []
    for r in rows:
        v = row_to_dict(r)
        v["alerts"] = vehicle_alerts(v) + vidange_km_alert(db, v)
        out.append(v)
    db.close()
    return jsonify({"vehicles": out})


@app.post("/api/vehicles")
@token_required
def create_vehicle():
    data = request.get_json(silent=True) or {}
    vals, error = validate_vehicle(data)
    if error:
        return err(error)
    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO vehicles (immatriculation, marque, modele, annee, type, carburant,
               kilometrage, vignette_exp, assurance_exp, ctrl_tech_exp, vignette_note, ct_note,
               carte_grise_note, statut, direction, affectation, num_chassis, num_moteur,
               carte_grise, carte_grise_exp, cv, lat, lng, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (vals["immatriculation"], vals["marque"], vals["modele"], vals["annee"], vals["type"],
             vals["carburant"], vals["kilometrage"], vals["vignette_exp"], vals["assurance_exp"],
             vals["ctrl_tech_exp"], vals["vignette_note"], vals["ct_note"], vals["carte_grise_note"],
             vals["statut"], vals["direction"], vals["affectation"], vals["num_chassis"],
             vals["num_moteur"], vals["carte_grise"], vals["carte_grise_exp"], vals["cv"],
             vals["lat"], vals["lng"], now()))
        db.commit()
        vid = cur.lastrowid
    except Exception:
        db.rollback()
        return err("Cette immatriculation existe déjà.", 409)
    finally:
        db.close()
    log_action("create", "vehicle", vid, {"immatriculation": vals["immatriculation"]})
    return jsonify({"id": vid, "ok": True, "message": "Véhicule ajouté."}), 201


@app.put("/api/vehicles/<int:vid>")
@token_required
def update_vehicle(vid):
    data = request.get_json(silent=True) or {}
    vals, error = validate_vehicle(data)
    if error:
        return err(error)
    db = get_db()
    try:
        cur = db.execute(
            """UPDATE vehicles SET immatriculation=?, marque=?, modele=?, annee=?, type=?,
               carburant=?, kilometrage=?, vignette_exp=?, assurance_exp=?, ctrl_tech_exp=?,
               vignette_note=?, ct_note=?, carte_grise_note=?, statut=?, direction=?,
               affectation=?, num_chassis=?, num_moteur=?, carte_grise=?, carte_grise_exp=?,
               cv=?, lat=?, lng=? WHERE id=?""",
            (vals["immatriculation"], vals["marque"], vals["modele"], vals["annee"], vals["type"],
             vals["carburant"], vals["kilometrage"], vals["vignette_exp"], vals["assurance_exp"],
             vals["ctrl_tech_exp"], vals["vignette_note"], vals["ct_note"], vals["carte_grise_note"],
             vals["statut"], vals["direction"], vals["affectation"], vals["num_chassis"],
             vals["num_moteur"], vals["carte_grise"], vals["carte_grise_exp"], vals["cv"],
             vals["lat"], vals["lng"], vid))
        db.commit()
        if cur.rowcount == 0:
            return err("Véhicule introuvable.", 404)
    except Exception as e:
        db.rollback()
        return err(f"Erreur de mise à jour : {e}", 409)
    finally:
        db.close()
    log_action("update", "vehicle", vid, {"immatriculation": vals["immatriculation"]})
    return jsonify({"ok": True, "message": "Véhicule mis à jour."})


@app.delete("/api/vehicles/<int:vid>")
@token_required
@admin_required
def delete_vehicle(vid):
    db = get_db()
    v = db.execute("SELECT immatriculation, photo, photo_thumb FROM vehicles WHERE id=?", (vid,)).fetchone()
    doc_files = [doc["stored"] for doc in db.execute("SELECT stored FROM documents WHERE vehicle_id=?", (vid,)).fetchall()]
    cur = db.execute("DELETE FROM vidanges WHERE vehicle_id=?", (vid,))
    db.execute("DELETE FROM odometer WHERE vehicle_id=?", (vid,))
    db.execute("DELETE FROM documents WHERE vehicle_id=?", (vid,))
    db.execute("DELETE FROM tires WHERE vehicle_id=?", (vid,))
    cur2 = db.execute("DELETE FROM vehicles WHERE id=?", (vid,))
    db.commit()
    db.close()
    if cur2.rowcount == 0:
        return err("Véhicule introuvable.", 404)
    _delete_vehicle_files(doc_files)
    if v is not None:
        _delete_vehicle_files([v["photo"], v["photo_thumb"]])
    log_action("delete", "vehicle", vid, {"immatriculation": v["immatriculation"] if v else None})
    return jsonify({"ok": True, "message": "Véhicule supprimé."})


# ---------------------------------------------------------------- conducteurs
@app.get("/api/drivers")
@token_required
def list_drivers():
    db = get_db()
    rows = db.execute("SELECT * FROM drivers ORDER BY nom, prenom").fetchall()
    db.close()
    return jsonify({"drivers": [row_to_dict(r) for r in rows]})


@app.post("/api/drivers")
@token_required
def create_driver():
    data = request.get_json(silent=True) or {}
    nom = (data.get("nom") or "").strip()
    prenom = (data.get("prenom") or "").strip()
    if not nom or not prenom:
        return err("Nom et prénom requis.")
    db = get_db()
    cur = db.execute(
        "INSERT INTO drivers (nom, prenom, matricule, email, telephone, permis, permis_exp, cni, cni_exp, permis_note, cni_note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (nom, prenom, (data.get("matricule") or "").strip() or None,
         (data.get("email") or "").strip(), (data.get("telephone") or "").strip(),
         (data.get("permis") or "").strip(), data.get("permis_exp"),
         (data.get("cni") or "").strip() or None, data.get("cni_exp"),
         (data.get("permis_note") or "").strip() or None,
         (data.get("cni_note") or "").strip() or None, now()))
    db.commit()
    db.close()
    log_action("create", "driver", cur.lastrowid, {"nom": nom, "prenom": prenom})
    return jsonify({"id": cur.lastrowid, "ok": True}), 201


@app.put("/api/drivers/<int:did>")
@token_required
def update_driver(did):
    data = request.get_json(silent=True) or {}
    nom = (data.get("nom") or "").strip()
    prenom = (data.get("prenom") or "").strip()
    if not nom or not prenom:
        return err("Nom et prénom requis.")
    db = get_db()
    cur = db.execute(
        "UPDATE drivers SET nom=?, prenom=?, matricule=?, email=?, telephone=?, permis=?, permis_exp=?, cni=?, cni_exp=?, permis_note=?, cni_note=? WHERE id=?",
        (nom, prenom, (data.get("matricule") or "").strip() or None,
         (data.get("email") or "").strip(), (data.get("telephone") or "").strip(),
         (data.get("permis") or "").strip(), data.get("permis_exp"),
         (data.get("cni") or "").strip() or None, data.get("cni_exp"),
         (data.get("permis_note") or "").strip() or None,
         (data.get("cni_note") or "").strip() or None, did))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Conducteur introuvable.", 404)
    log_action("update", "driver", did, {"nom": nom, "prenom": prenom})
    return jsonify({"ok": True})


@app.delete("/api/drivers/<int:did>")
@token_required
@admin_required
def delete_driver(did):
    db = get_db()
    d = db.execute("SELECT nom, prenom FROM drivers WHERE id=?", (did,)).fetchone()
    cur = db.execute("DELETE FROM drivers WHERE id=?", (did,))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Conducteur introuvable.", 404)
    log_action("delete", "driver", did,
               {"nom": d["nom"] if d else None, "prenom": d["prenom"] if d else None})
    return jsonify({"ok": True})


# ---------------------------------------------------------------- contrôles
@app.get("/api/controls")
@token_required
def list_controls():
    db = get_db()
    rows = db.execute(
        """SELECT c.*, v.immatriculation, v.marque, v.modele, d.nom AS d_nom, d.prenom AS d_prenom
           FROM controls c
           LEFT JOIN vehicles v ON v.id = c.vehicle_id
           LEFT JOIN drivers d ON d.id = c.driver_id
           ORDER BY c.date DESC, c.id DESC""").fetchall()
    db.close()
    return jsonify({"controls": [row_to_dict(r) for r in rows]})


@app.get("/api/controls/vehicle/<int:vid>")
@token_required
def vehicle_controls(vid):
    db = get_db()
    rows = db.execute("SELECT * FROM controls WHERE vehicle_id=? ORDER BY date DESC", (vid,)).fetchall()
    db.close()
    return jsonify({"controls": [row_to_dict(r) for r in rows]})


@app.post("/api/controls")
@token_required
def create_control():
    data = request.get_json(silent=True) or {}
    vid = data.get("vehicle_id")
    if not vid:
        return err("Véhicule requis.")
    date_ct = data.get("date") or today()
    db = get_db()
    if db.execute("SELECT 1 FROM vehicles WHERE id=?", (vid,)).fetchone() is None:
        db.close()
        return err("Véhicule inconnu.", 404)
    cur = db.execute(
        "INSERT INTO controls (vehicle_id, driver_id, date, type, resultat, notes, items, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (vid, data.get("driver_id"), date_ct, data.get("type") or "Contrôle technique",
         data.get("resultat") or "En cours", (data.get("notes") or "").strip(),
         json.dumps(parse_items(data.get("items")), ensure_ascii=False), now()))
    db.commit()
    db.close()
    log_action("create", "control", cur.lastrowid, {"vehicle_id": vid, "date": date_ct})
    return jsonify({"id": cur.lastrowid, "ok": True}), 201


@app.put("/api/controls/<int:cid>")
@token_required
def update_control(cid):
    data = request.get_json(silent=True) or {}
    db = get_db()
    cur = db.execute(
        "UPDATE controls SET vehicle_id=?, driver_id=?, date=?, type=?, resultat=?, notes=?, items=? WHERE id=?",
        (data.get("vehicle_id"), data.get("driver_id"), data.get("date") or today(),
         data.get("type") or "Contrôle technique", data.get("resultat") or "En cours",
         (data.get("notes") or "").strip(), json.dumps(parse_items(data.get("items")), ensure_ascii=False), cid))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Contrôle introuvable.", 404)
    log_action("update", "control", cid, {"date": data.get("date") or today()})
    return jsonify({"ok": True})


@app.delete("/api/controls/<int:cid>")
@token_required
@admin_required
def delete_control(cid):
    db = get_db()
    cur = db.execute("DELETE FROM controls WHERE id=?", (cid,))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Contrôle introuvable.", 404)
    log_action("delete", "control", cid, {})
    return jsonify({"ok": True})


# ---------------------------------------------------------------- maintenance
@app.get("/api/maintenance")
@token_required
def list_maintenance():
    db = get_db()
    rows = db.execute(
        """SELECT m.*, v.immatriculation, v.marque, v.modele
           FROM maintenance m LEFT JOIN vehicles v ON v.id = m.vehicle_id
           ORDER BY m.date DESC, m.id DESC""").fetchall()
    db.close()
    return jsonify({"maintenance": [row_to_dict(r) for r in rows]})


@app.post("/api/maintenance")
@token_required
def create_maintenance():
    data = request.get_json(silent=True) or {}
    vid = data.get("vehicle_id")
    if not vid:
        return err("Véhicule requis.")
    db = get_db()
    if db.execute("SELECT 1 FROM vehicles WHERE id=?", (vid,)).fetchone() is None:
        db.close()
        return err("Véhicule inconnu.", 404)
    cur = db.execute(
        "INSERT INTO maintenance (vehicle_id, type, date, cout, garage, notes, created_at) VALUES (?,?,?,?,?,?,?)",
        (vid, data.get("type") or "Révision", data.get("date") or today(),
         float(data.get("cout") or 0), (data.get("garage") or "").strip(),
         (data.get("notes") or "").strip(), now()))
    db.commit()
    db.close()
    log_action("create", "maintenance", cur.lastrowid, {"vehicle_id": vid, "type": data.get("type")})
    return jsonify({"id": cur.lastrowid, "ok": True}), 201


@app.put("/api/maintenance/<int:mid>")
@token_required
def update_maintenance(mid):
    data = request.get_json(silent=True) or {}
    db = get_db()
    cur = db.execute(
        "UPDATE maintenance SET vehicle_id=?, type=?, date=?, cout=?, garage=?, notes=? WHERE id=?",
        (data.get("vehicle_id"), data.get("type") or "Révision", data.get("date") or today(),
         float(data.get("cout") or 0), (data.get("garage") or "").strip(),
         (data.get("notes") or "").strip(), mid))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Intervention introuvable.", 404)
    log_action("update", "maintenance", mid, {"type": data.get("type")})
    return jsonify({"ok": True})


@app.delete("/api/maintenance/<int:mid>")
@token_required
@admin_required
def delete_maintenance(mid):
    db = get_db()
    cur = db.execute("DELETE FROM maintenance WHERE id=?", (mid,))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Intervention introuvable.", 404)
    log_action("delete", "maintenance", mid, {})
    return jsonify({"ok": True})


# ---------------------------------------------------------------- vidanges
def _vidange_next_km(db, km):
    """Kilométrage de la prochaine vidange (km actuel + intervalle paramétré)."""
    try:
        interval = max(500, int(get_setting("forecast_km", "10000")))
    except (ValueError, TypeError):
        interval = 10000
    return max(km or 0, 0) + interval


def _vg_int(data, key):
    try:
        return max(0, int(float(data.get(key) or 0)))
    except (ValueError, TypeError):
        return 0


def _vg_bool(data, key):
    return 1 if data.get(key) else 0


def _vg_prochaine(db, data, km, km_interval):
    """Prochaine vidange = km à la vidange + km de la vidange (intervalle).
    L'intervalle renseigné prime ; sinon on garde la valeur saisie
    (prochaine_km) ; sinon km + intervalle paramétré."""
    if km_interval:
        return km + km_interval
    manual = _vg_int(data, "prochaine_km")
    if manual:
        return manual
    return _vidange_next_km(db, km)


@app.get("/api/vidanges")
@token_required
def list_vidanges():
    vehicle_id = request.args.get("vehicle_id")
    sql = ("SELECT vg.*, v.immatriculation, v.marque, v.modele "
           "FROM vidanges vg LEFT JOIN vehicles v ON v.id = vg.vehicle_id WHERE 1=1")
    params = []
    if vehicle_id:
        sql += " AND vg.vehicle_id=?"
        params.append(vehicle_id)
    sql += " ORDER BY vg.date DESC, vg.id DESC"
    db = get_db()
    rows = db.execute(sql, params).fetchall()
    db.close()
    return jsonify({"vidanges": [row_to_dict(r) for r in rows]})


@app.post("/api/vidanges")
@token_required
def create_vidange():
    data = request.get_json(silent=True) or {}
    vid = data.get("vehicle_id")
    if not vid:
        return err("Véhicule requis.")
    db = get_db()
    if db.execute("SELECT 1 FROM vehicles WHERE id=?", (vid,)).fetchone() is None:
        db.close()
        return err("Véhicule inconnu.", 404)
    km = _vg_int(data, "km")
    km_interval = _vg_int(data, "km_interval")
    filtre_huile = _vg_bool(data, "filtre") or _vg_bool(data, "filtre_huile")
    prochaine = _vg_prochaine(db, data, km, km_interval)
    cur = db.execute(
        """INSERT INTO vidanges (vehicle_id, date, km, huile, quantite, filtre,
           filtre_huile, filtre_gasoil, huile_transmission,
           liquide_refroidissement, liquide_laveglace, km_interval,
           cout, garage, notes, prochaine_km, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (vid, data.get("date") or today(), km, (data.get("huile") or "").strip(),
         float(data.get("quantite") or 0), filtre_huile,
         filtre_huile, _vg_bool(data, "filtre_gasoil"),
         _vg_bool(data, "huile_transmission"), _vg_bool(data, "liquide_refroidissement"),
         _vg_bool(data, "liquide_laveglace"), km_interval,
         float(data.get("cout") or 0), (data.get("garage") or "").strip(),
         (data.get("notes") or "").strip(), prochaine, now()))
    db.commit()
    db.close()
    log_action("create", "vidange", cur.lastrowid, {"vehicle_id": vid, "km": km})
    return jsonify({"id": cur.lastrowid, "ok": True}), 201


@app.put("/api/vidanges/<int:vgid>")
@token_required
def update_vidange(vgid):
    data = request.get_json(silent=True) or {}
    km = _vg_int(data, "km")
    km_interval = _vg_int(data, "km_interval")
    filtre_huile = _vg_bool(data, "filtre") or _vg_bool(data, "filtre_huile")
    db = get_db()
    prochaine = _vg_prochaine(db, data, km, km_interval)
    cur = db.execute(
        """UPDATE vidanges SET vehicle_id=?, date=?, km=?, huile=?, quantite=?, filtre=?,
           filtre_huile=?, filtre_gasoil=?, huile_transmission=?,
           liquide_refroidissement=?, liquide_laveglace=?, km_interval=?,
           cout=?, garage=?, notes=?, prochaine_km=? WHERE id=?""",
        (data.get("vehicle_id"), data.get("date") or today(), km,
         (data.get("huile") or "").strip(), float(data.get("quantite") or 0),
         filtre_huile, filtre_huile, _vg_bool(data, "filtre_gasoil"),
         _vg_bool(data, "huile_transmission"), _vg_bool(data, "liquide_refroidissement"),
         _vg_bool(data, "liquide_laveglace"), km_interval,
         float(data.get("cout") or 0), (data.get("garage") or "").strip(),
         (data.get("notes") or "").strip(), prochaine, vgid))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Vidange introuvable.", 404)
    log_action("update", "vidange", vgid, {"km": km})
    return jsonify({"ok": True})


@app.delete("/api/vidanges/<int:vgid>")
@token_required
@admin_required
def delete_vidange(vgid):
    db = get_db()
    cur = db.execute("DELETE FROM vidanges WHERE id=?", (vgid,))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Vidange introuvable.", 404)
    log_action("delete", "vidange", vgid, {})
    return jsonify({"ok": True})


@app.get("/api/vidanges/stats")
@token_required
def vidanges_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM vidanges").fetchone()["n"]
    cost_total = float(db.execute(
        "SELECT COALESCE(SUM(cout),0) AS n FROM vidanges").fetchone()["n"])
    year = str(date.today().year)
    this_year = db.execute(
        "SELECT COUNT(*) AS n FROM vidanges WHERE substr(date,1,4)=?", (year,)).fetchone()["n"]
    by_vehicle = [dict(r) for r in db.execute(
        """SELECT v.id AS vehicle_id, v.immatriculation, v.marque, v.modele,
                  COUNT(vg.id) AS count, COALESCE(SUM(vg.cout),0) AS cout
           FROM vehicles v LEFT JOIN vidanges vg ON vg.vehicle_id = v.id
           GROUP BY v.id ORDER BY cout DESC""").fetchall()]
    try:
        interval = max(500, int(get_setting("forecast_km", "10000")))
    except (ValueError, TypeError):
        interval = 10000
    latest = {}
    for r in db.execute(
            """SELECT vg.*, v.immatriculation, v.marque, v.modele, v.kilometrage
               FROM vidanges vg JOIN vehicles v ON v.id = vg.vehicle_id
               ORDER BY vg.date DESC, vg.id DESC""").fetchall():
        latest.setdefault(r["vehicle_id"], dict(r))
    forecast = []
    for v in latest.values():
        km_now = v.get("kilometrage") or 0
        km_due = v.get("prochaine_km") or ((v.get("km") or 0) + interval)
        km_left = km_due - km_now
        last_date = None
        if v.get("date"):
            try:
                last_date = datetime.strptime(v["date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                last_date = None
        days_since = (date.today() - last_date).days if last_date is not None else None
        due = km_left <= 0 or (days_since is not None and days_since > 365)
        forecast.append({
            "vehicle_id": v["vehicle_id"], "immatriculation": v["immatriculation"],
            "marque": v["marque"], "modele": v["modele"],
            "last_date": v.get("date"), "km": v.get("km") or 0, "km_due": km_due,
            "km_now": km_now, "km_left": km_left, "days_since": days_since, "due": due,
        })
    forecast.sort(key=lambda x: (x["due"], x["km_left"]))
    db.close()
    return jsonify({
        "total": total, "cost_total": cost_total, "this_year": this_year,
        "by_vehicle": by_vehicle, "forecast": forecast,
    })


@app.get("/api/vidanges/pdf")
@token_required
def vidanges_pdf():
    db = get_db()
    rows = [dict(r) for r in db.execute(
        """SELECT vg.*, v.immatriculation, v.marque, v.modele, v.kilometrage
           FROM vidanges vg LEFT JOIN vehicles v ON v.id = vg.vehicle_id
           ORDER BY vg.date DESC, vg.id DESC""").fetchall()]
    total_cost = sum(float(r.get("cout") or 0) for r in rows)
    year = str(date.today().year)
    year_count = sum(1 for r in rows if str(r.get("date") or "").startswith(year))
    by_veh = {}
    for r in rows:
        k = r.get("immatriculation") or "—"
        b = by_veh.setdefault(k, {"immatriculation": k, "marque": r.get("marque"),
                                  "modele": r.get("modele"), "count": 0, "cout": 0.0})
        b["count"] += 1
        b["cout"] += float(r.get("cout") or 0)
    db.close()
    data = pdfgen.vidanges_report(
        rows, total_cost, sorted(by_veh.values(), key=lambda x: -x["cout"]), year_count)
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"rapport_vidanges_{date.today().isoformat()}.pdf",
                     mimetype="application/pdf")


# ---------------------------------------------------------------- fichiers & photos
def _safe_ext(filename):
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif") else ".jpg"


def _make_photo_thumb(raw, stem, size=320):
    """Génère une miniature (JPEG) pour la photo d'un véhicule.

    Retourne le chemin public ('/uploads/…') ou None si l'image est invalide.
    """
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        name = f"{stem}_thumb.jpg"
        img.save(os.path.join(UPLOAD_DIR, name), "JPEG", quality=82, optimize=True)
        return "/uploads/" + name
    except Exception:
        return None


def _delete_vehicle_files(paths):
    for path in paths or []:
        if not path:
            continue
        try:
            fp = os.path.join(UPLOAD_DIR, os.path.basename(path))
            if os.path.isfile(fp):
                os.remove(fp)
        except OSError:
            pass


ALLOWED_DOC = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".odt"}


@app.get("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, os.path.basename(filename))


@app.post("/api/vehicles/<int:vid>/photo")
@token_required
def upload_photo(vid):
    db = get_db()
    v = db.execute("SELECT photo, photo_thumb FROM vehicles WHERE id=?", (vid,)).fetchone()
    if v is None:
        db.close()
        return err("Véhicule introuvable.", 404)
    f = request.files.get("photo")
    if f is None or not f.filename:
        db.close()
        return err("Aucun fichier fourni.")
    raw = f.read()
    if not raw:
        db.close()
        return err("Fichier vide.")
    if len(raw) > 5 * 1024 * 1024:
        db.close()
        return err("Image trop lourde (5 Mo max).")
    ext = _safe_ext(f.filename)
    stem = f"veh_{vid}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    stored = stem + ext
    with open(os.path.join(UPLOAD_DIR, stored), "wb") as out:
        out.write(raw)
    thumb = _make_photo_thumb(raw, stem)
    if thumb is None:
        _delete_vehicle_files(["/uploads/" + stored])
        db.close()
        return err("Image invalide (format non reconnu).", 400)
    old = v["photo"]
    old_thumb = v["photo_thumb"]
    db.execute("UPDATE vehicles SET photo=?, photo_thumb=? WHERE id=?",
               ("/uploads/" + stored, thumb, vid))
    db.commit()
    db.close()
    _delete_vehicle_files([old, old_thumb])
    log_action("update", "vehicle", vid, {"photo": True})
    return jsonify({"ok": True, "photo": "/uploads/" + stored, "photo_thumb": thumb})


@app.delete("/api/vehicles/<int:vid>/photo")
@token_required
def delete_photo(vid):
    db = get_db()
    v = db.execute("SELECT photo, photo_thumb FROM vehicles WHERE id=?", (vid,)).fetchone()
    if v is None:
        db.close()
        return err("Véhicule introuvable.", 404)
    old = v["photo"]
    old_thumb = v["photo_thumb"]
    db.execute("UPDATE vehicles SET photo=NULL, photo_thumb=NULL WHERE id=?", (vid,))
    db.commit()
    db.close()
    _delete_vehicle_files([old, old_thumb])
    log_action("update", "vehicle", vid, {"photo": False})
    return jsonify({"ok": True})


# ---------------------------------------------------------------- relevés kilométriques
@app.get("/api/vehicles/<int:vid>/odometer")
@token_required
def list_odometer(vid):
    db = get_db()
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM odometer WHERE vehicle_id=? ORDER BY date DESC, id DESC", (vid,)).fetchall()]
    db.close()
    return jsonify({"odometer": rows})


@app.post("/api/vehicles/<int:vid>/odometer")
@token_required
def add_odometer(vid):
    data = request.get_json(silent=True) or {}
    db = get_db()
    if db.execute("SELECT 1 FROM vehicles WHERE id=?", (vid,)).fetchone() is None:
        db.close()
        return err("Véhicule inconnu.", 404)
    km = data.get("kilometres")
    try:
        km = max(0, int(km))
    except (ValueError, TypeError):
        db.close()
        return err("Kilométrage invalide.")
    date_val = data.get("date") or today()
    if not DATE_OK(date_val):
        db.close()
        return err("Date invalide (format AAAA-MM-JJ).")
    cur = db.execute(
        "INSERT INTO odometer (vehicle_id, date, kilometres, note, created_at) VALUES (?,?,?,?,?)",
        (vid, date_val, km, (data.get("note") or "").strip(), now()))
    db.commit()
    db.close()
    log_action("create", "odometer", cur.lastrowid, {"vehicle_id": vid, "kilometres": km})
    return jsonify({"id": cur.lastrowid, "ok": True}), 201


@app.delete("/api/odometer/<int:oid>")
@token_required
def delete_odometer(oid):
    db = get_db()
    cur = db.execute("DELETE FROM odometer WHERE id=?", (oid,))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Relevé introuvable.", 404)
    log_action("delete", "odometer", oid, {})
    return jsonify({"ok": True})


# ---------------------------------------------------------------- documents par véhicule
@app.get("/api/vehicles/<int:vid>/documents")
@token_required
def list_documents(vid):
    db = get_db()
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM documents WHERE vehicle_id=? ORDER BY created_at DESC", (vid,)).fetchall()]
    db.close()
    return jsonify({"documents": rows})


@app.post("/api/vehicles/<int:vid>/documents")
@token_required
def upload_document(vid):
    db = get_db()
    if db.execute("SELECT 1 FROM vehicles WHERE id=?", (vid,)).fetchone() is None:
        db.close()
        return err("Véhicule inconnu.", 404)
    f = request.files.get("file")
    if f is None or not f.filename:
        db.close()
        return err("Aucun fichier fourni.")
    raw = f.read()
    if not raw:
        db.close()
        return err("Fichier vide.")
    if len(raw) > 10 * 1024 * 1024:
        db.close()
        return err("Fichier trop lourd (10 Mo max).")
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_DOC:
        db.close()
        return err("Type de fichier non autorisé.")
    label = (request.form.get("label") or "").strip() or f.filename
    stored = f"doc_{vid}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"
    with open(os.path.join(UPLOAD_DIR, stored), "wb") as out:
        out.write(raw)
    cur = db.execute(
        "INSERT INTO documents (vehicle_id, label, filename, stored, created_at) VALUES (?,?,?,?,?)",
        (vid, label, f.filename, "/uploads/" + stored, now()))
    db.commit()
    db.close()
    log_action("create", "document", cur.lastrowid, {"vehicle_id": vid, "label": label})
    return jsonify({"id": cur.lastrowid, "ok": True}), 201


@app.delete("/api/documents/<int:did>")
@token_required
def delete_document(did):
    db = get_db()
    row = db.execute("SELECT * FROM documents WHERE id=?", (did,)).fetchone()
    if row is None:
        db.close()
        return err("Document introuvable.", 404)
    db.execute("DELETE FROM documents WHERE id=?", (did,))
    db.commit()
    db.close()
    _delete_vehicle_files([row["stored"]])
    log_action("delete", "document", did, {"label": row["label"]})
    return jsonify({"ok": True})


# ---------------------------------------------------------------- pneumatiques
TIRE_POSITIONS = ["AVG", "AVD", "ARG", "ARD"]


@app.get("/api/vehicles/<int:vid>/tires")
@token_required
def list_tires(vid):
    db = get_db()
    rows = [dict(r) for r in db.execute(
        "SELECT * FROM tires WHERE vehicle_id=? ORDER BY id", (vid,)).fetchall()]
    db.close()
    return jsonify({"tires": rows})


@app.post("/api/vehicles/<int:vid>/tires")
@token_required
def add_tire(vid):
    data = request.get_json(silent=True) or {}
    db = get_db()
    if db.execute("SELECT 1 FROM vehicles WHERE id=?", (vid,)).fetchone() is None:
        db.close()
        return err("Véhicule inconnu.", 404)
    pos = (data.get("position") or "AVG").strip().upper()
    if pos not in TIRE_POSITIONS:
        db.close()
        return err("Position invalide (AVG, AVD, ARG, ARD).")
    cur = db.execute(
        """INSERT INTO tires (vehicle_id, position, marque, taille, etat, date_montage, date_remplacement, note, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (vid, pos, (data.get("marque") or "").strip(), (data.get("taille") or "").strip(),
         data.get("etat") or "Bon", data.get("date_montage"), data.get("date_remplacement"),
         (data.get("note") or "").strip(), now()))
    db.commit()
    db.close()
    log_action("create", "tire", cur.lastrowid, {"vehicle_id": vid, "position": pos})
    return jsonify({"id": cur.lastrowid, "ok": True}), 201


@app.put("/api/tires/<int:tid>")
@token_required
def update_tire(tid):
    data = request.get_json(silent=True) or {}
    pos = (data.get("position") or "AVG").strip().upper()
    if pos not in TIRE_POSITIONS:
        return err("Position invalide (AVG, AVD, ARG, ARD).")
    db = get_db()
    cur = db.execute(
        """UPDATE tires SET position=?, marque=?, taille=?, etat=?, date_montage=?, date_remplacement=?, note=? WHERE id=?""",
        (pos, (data.get("marque") or "").strip(), (data.get("taille") or "").strip(),
         data.get("etat") or "Bon", data.get("date_montage"), data.get("date_remplacement"),
         (data.get("note") or "").strip(), tid))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Pneumatique introuvable.", 404)
    log_action("update", "tire", tid, {})
    return jsonify({"ok": True})


@app.delete("/api/tires/<int:tid>")
@token_required
def delete_tire(tid):
    db = get_db()
    cur = db.execute("DELETE FROM tires WHERE id=?", (tid,))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Pneumatique introuvable.", 404)
    log_action("delete", "tire", tid, {})
    return jsonify({"ok": True})


# ---------------------------------------------------------------- paramètres
@app.get("/api/settings")
@token_required
def get_settings():
    db = get_db()
    rows = {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM settings").fetchall()}
    db.close()
    return jsonify({"settings": {
        "alert_threshold": int(rows.get("alert_threshold") or 30),
        "forecast_km": int(rows.get("forecast_km") or 10000),
        "vidange_alert_km": int(rows.get("vidange_alert_km") or VIDANGE_ALERT_KM),
        "notify_enabled": rows.get("notify_enabled", "0") == "1",
        "notify_emails": rows.get("notify_emails", "") or "",
        "notify_hour": int(rows.get("notify_hour") or 7),
        "smtp_host": rows.get("smtp_host", "") or "",
        "smtp_port": int(rows.get("smtp_port") or 587),
        "smtp_user": rows.get("smtp_user", "") or "",
        "smtp_pass_set": bool(rows.get("smtp_pass")),
        "smtp_from": rows.get("smtp_from", "") or "",
        "smtp_tls": rows.get("smtp_tls", "1") == "1",
        "last_digest_sent": rows.get("last_digest_sent", "") or "",
        "assistant_ai_enabled": assistant.ai_available(),
        "assistant_api_key_set": bool((rows.get("openrouter_api_key") or "").strip()),
        "assistant_env_key_set": bool(os.environ.get("OPENROUTER_API_KEY")),
        "assistant_model": rows.get("assistant_model", "") or "",
        "google_maps_key": rows.get("google_maps_key", "") or "",
    }})


@app.put("/api/settings")
@token_required
@admin_required
def update_settings():
    data = request.get_json(silent=True) or {}
    if "alert_threshold" in data:
        try:
            set_setting("alert_threshold", str(max(1, min(365, int(data["alert_threshold"])))))
        except (ValueError, TypeError):
            return err("Seuil d'alerte invalide (1 à 365 jours).")
    if "forecast_km" in data:
        try:
            set_setting("forecast_km", str(max(500, min(100000, int(data["forecast_km"])))))
        except (ValueError, TypeError):
            return err("Intervalle de prévision invalide.")
    if "vidange_alert_km" in data:
        try:
            set_setting("vidange_alert_km", str(max(100, min(10000, int(data["vidange_alert_km"])))))
        except (ValueError, TypeError):
            return err("Seuil d'alerte vidange invalide (100 à 10000 km).")
    if "notify_enabled" in data:
        set_setting("notify_enabled", "1" if data["notify_enabled"] else "0")
    if "notify_emails" in data:
        set_setting("notify_emails", ", ".join(
            e.strip() for e in re.split(r"[,;\s]+", str(data["notify_emails"])) if e.strip()))
    if "notify_hour" in data:
        try:
            set_setting("notify_hour", str(max(0, min(23, int(data["notify_hour"])))))
        except (ValueError, TypeError):
            return err("Heure d'envoi invalide (0 à 23).")
    if "smtp_host" in data:
        set_setting("smtp_host", str(data["smtp_host"] or "").strip())
    if "smtp_port" in data:
        try:
            set_setting("smtp_port", str(max(1, min(65535, int(data["smtp_port"] or 587)))))
        except (ValueError, TypeError):
            return err("Port SMTP invalide.")
    if "smtp_user" in data:
        set_setting("smtp_user", str(data["smtp_user"] or "").strip())
    if "smtp_pass" in data and str(data["smtp_pass"] or "").strip():
        set_setting("smtp_pass", str(data["smtp_pass"]).strip())
    if "smtp_from" in data:
        set_setting("smtp_from", str(data["smtp_from"] or "").strip())
    if "smtp_tls" in data:
        set_setting("smtp_tls", "1" if data["smtp_tls"] else "0")
    if "openrouter_api_key" in data and str(data["openrouter_api_key"] or "").strip():
        set_setting("openrouter_api_key", str(data["openrouter_api_key"]).strip())
    if "assistant_model" in data:
        set_setting("assistant_model", str(data["assistant_model"] or "").strip())
    if "google_maps_key" in data:
        set_setting("google_maps_key", str(data["google_maps_key"] or "").strip())
    log_action("update", "settings", None, {"keys": list(data.keys())})
    return jsonify({"ok": True, "message": "Paramètres mis à jour."})


# ---------------------------------------------------------------- calendrier
@app.get("/api/calendar/events")
@token_required
def calendar_events():
    db = get_db()
    events = []
    for v in [dict(r) for r in db.execute("SELECT * FROM vehicles").fetchall()]:
        for key, label in (("assurance_exp", "Assurance"), ("vignette_exp", "Vignette"),
                           ("ctrl_tech_exp", "Contrôle technique"), ("carte_grise_exp", "Carte grise")):
            d = v.get(key)
            if d:
                events.append({"date": d, "type": key, "label": label,
                               "vehicle": f"{v['marque']} {v['modele']}",
                               "immatriculation": v["immatriculation"], "kind": "vehicle"})
    for d in [dict(r) for r in db.execute("SELECT * FROM drivers").fetchall()]:
        if d.get("permis_exp"):
            events.append({"date": d["permis_exp"], "type": "permis", "label": "Permis",
                           "vehicle": f"{d['prenom']} {d['nom']}",
                           "immatriculation": d.get("permis") or "", "kind": "driver"})
        if d.get("cni_exp"):
            events.append({"date": d["cni_exp"], "type": "cni", "label": "Carte identité",
                           "vehicle": f"{d['prenom']} {d['nom']}",
                           "immatriculation": "", "kind": "driver"})
    for vg in [dict(r) for r in db.execute(
            """SELECT vg.date, vg.km, vg.vehicle_id, v.immatriculation, v.marque, v.modele
               FROM vidanges vg LEFT JOIN vehicles v ON v.id = vg.vehicle_id
               WHERE vg.date IS NOT NULL AND vg.date != ''
               ORDER BY vg.date DESC, vg.id DESC""").fetchall()]:
        if vg.get("date"):
            events.append({"date": vg["date"], "type": "vidange", "label": "Vidange",
                           "vehicle": f"{vg['marque'] or ''} {vg['modele'] or ''}".strip() or "—",
                           "immatriculation": vg.get("immatriculation") or "",
                           "kind": "vehicle", "km": vg.get("km") or 0})
    db.close()
    events.sort(key=lambda e: e["date"])
    return jsonify({"events": events})


# ---------------------------------------------------------------- prévisions de maintenance (prédictif)
FORECAST_RULES = {
    "Révision": {"km": 10000, "days": 365},
    "Vidange": {"km": 10000, "days": 365},
    "Freinage": {"km": 30000, "days": 730},
    "Pneumatique": {"km": 40000, "days": 1460},
    "Batterie": {"km": 60000, "days": 1460},
    "Climatisation": {"km": 40000, "days": 730},
    "Tôlerie": {"km": 50000, "days": 1095},
    "Électronique": {"km": 50000, "days": 730},
    "Moteur": {"km": 80000, "days": 1460},
    "Pompes": {"km": 60000, "days": 1095},
    "Administratif": {"km": 999999, "days": 365},
    "Autre": {"km": 50000, "days": 730},
}


def _vehicle_km_per_day(db, vehicle_id, fallback_km, fallback_days):
    """Estime le rythme kilométrique réel du véhicule à partir de ses relevés
    d'odomètre, pour convertir un seuil km en échéance calendaire fiable."""
    rows = [dict(r) for r in db.execute(
        "SELECT date, kilometres FROM odometer WHERE vehicle_id=? ORDER BY date ASC", (vehicle_id,)).fetchall()]
    pts = []
    for r in rows:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d").date()
            pts.append((d, r["kilometres"] or 0))
        except (ValueError, TypeError):
            continue
    if len(pts) >= 2:
        (d0, k0), (d1, k1) = pts[0], pts[-1]
        days = max(1, (d1 - d0).days)
        rate = (k1 - k0) / days
        if rate > 0.1:
            return rate
    if fallback_days:
        return max(fallback_km, 0) / max(fallback_days, 1)
    return 30.0  # ~900 km/mois par défaut, hypothèse prudente


def compute_maintenance_forecast(db):
    """Prévision de maintenance par véhicule et par catégorie : utilise
    l'historique réel du véhicule (intervalle moyen km/jours entre ses
    propres interventions) quand il y en a assez, sinon les règles par
    défaut ; le coût prévisionnel s'appuie sur le coût moyen observé, ou à
    défaut le prix unitaire moyen du plan budgétaire importé."""
    vehicles = [dict(r) for r in db.execute("SELECT * FROM vehicles").fetchall()]
    try:
        default_interval = max(500, int(get_setting("forecast_km", "10000")))
    except (ValueError, TypeError):
        default_interval = 10000
    today_d = date.today()
    annee = today_d.year
    out = []

    for v in vehicles:
        km_now = v.get("kilometrage") or 0
        history = [dict(r) for r in db.execute(
            "SELECT type, date, cout FROM maintenance WHERE vehicle_id=? ORDER BY date ASC, id ASC",
            (v["id"],)).fetchall()]
        by_cat = {}
        for r in history:
            cat = budget_module.normalize_categorie(r["type"])
            by_cat.setdefault(cat, []).append(r)

        # catégories à évaluer : celles déjà rencontrées pour ce véhicule,
        # plus au minimum "Révision" pour garantir une échéance par défaut.
        cats_to_check = set(by_cat.keys()) or set()
        cats_to_check.add("Révision")

        vehicle_candidates = []
        for cat in cats_to_check:
            records = by_cat.get(cat, [])
            rule = FORECAST_RULES.get(cat, FORECAST_RULES["Autre"])
            method = "regle"
            interval_days = rule["days"]
            interval_km = rule["km"] if records else default_interval
            last_date, last_cost = None, None

            if records:
                last = records[-1]
                try:
                    last_date = datetime.strptime(last["date"], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    last_date = None
                last_cost = last.get("cout")

            if len(records) >= 2:
                dates = []
                for r in records:
                    try:
                        dates.append(datetime.strptime(r["date"], "%Y-%m-%d").date())
                    except (ValueError, TypeError):
                        pass
                if len(dates) >= 2:
                    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
                    avg_gap = sum(gaps) / len(gaps)
                    if avg_gap > 5:
                        interval_days = int(round(avg_gap))
                        method = "historique"

            date_due = (last_date or today_d) + timedelta(days=interval_days)
            days_left = (date_due - today_d).days

            km_rate = _vehicle_km_per_day(db, v["id"], interval_km, interval_days)
            km_due = km_now + max(0, int(km_rate * max(days_left, 0)))
            if records:
                km_due = km_now + interval_km if method == "regle" else km_due

            predicted_cost = last_cost if last_cost else None
            if not predicted_cost:
                avg_cost_row = db.execute(
                    "SELECT AVG(cout) c FROM maintenance WHERE substr(date,1,4)=?", (str(annee),)).fetchone()
                predicted_cost = budget_module.prix_unitaire_moyen(db, annee, cat) or (avg_cost_row["c"] if avg_cost_row and avg_cost_row["c"] else 0) or 0

            vehicle_candidates.append({
                "vehicle_id": v["id"], "immatriculation": v["immatriculation"],
                "marque": v["marque"], "modele": v["modele"],
                "type": cat, "km_due": km_due, "date_due": date_due.isoformat(),
                "days_left": days_left, "last_date": last_date.isoformat() if last_date else None,
                "level": "danger" if days_left < 0 else ("warning" if days_left <= 30 else "ok"),
                "predicted_cost": round(float(predicted_cost or 0), 2),
                "method": method,
            })

        vehicle_candidates.sort(key=lambda x: x["days_left"])
        out.extend(vehicle_candidates)

    # `out` contient toutes les catégories prédites pour tous les véhicules ;
    # les usages « une échéance par véhicule » filtrent ensuite au besoin.
    out.sort(key=lambda x: x["days_left"])
    return out


@app.get("/api/maintenance/forecast")
@token_required
def maintenance_forecast():
    db = get_db()
    out = compute_maintenance_forecast(db)
    db.close()
    # vue par défaut : une échéance par véhicule (la plus proche)
    seen = set()
    headline = []
    for f in out:
        if f["vehicle_id"] in seen:
            continue
        seen.add(f["vehicle_id"])
        headline.append(f)
    return jsonify({"forecast": headline, "forecast_detail": out})


@app.get("/api/maintenance/forecast/budget")
@token_required
def maintenance_forecast_budget():
    """Budget prévisionnel glissant : somme des coûts prédits pour les
    interventions à venir sous 30 / 60 / 90 jours, toutes catégories."""
    db = get_db()
    out = compute_maintenance_forecast(db)
    db.close()
    horizons = {30: 0.0, 60: 0.0, 90: 0.0}
    counts = {30: 0, 60: 0, 90: 0}
    for f in out:
        if f["days_left"] < 0:
            continue
        for h in horizons:
            if f["days_left"] <= h:
                horizons[h] += float(f.get("predicted_cost") or 0)
                counts[h] += 1
    return jsonify({
        "horizon_30j": round(horizons[30], 2), "count_30j": counts[30],
        "horizon_60j": round(horizons[60], 2), "count_60j": counts[60],
        "horizon_90j": round(horizons[90], 2), "count_90j": counts[90],
    })


@app.get("/api/maintenance/categories")
@token_required
def maintenance_categories():
    return jsonify({"categories": budget_module.CATEGORIES})


# ---------------------------------------------------------------- budget & plan de maintenance
@app.post("/api/budget/import")
@token_required
@admin_required
def budget_import():
    f = request.files.get("file")
    if f is None or not f.filename:
        return err("Aucun fichier fourni.")
    if not f.filename.lower().endswith(".xlsx"):
        return err("Format non supporté : utilisez le fichier .xlsx du plan d'achat annuel.")
    raw = f.read()
    if not raw:
        return err("Fichier vide.")
    try:
        rows, meta = budget_module.parse_budget_workbook(raw, f.filename)
    except ValueError as e:
        return err(str(e))
    except Exception as e:
        return err(f"Analyse du fichier impossible : {e}")

    annee = request.args.get("annee", type=int) or meta["annee"]
    for r in rows:
        r["annee"] = annee
    db = get_db()
    budget_module.replace_budget_plan(db, annee, rows)
    db.close()
    log_action("import", "budget_plan", None, {"annee": annee, "rows": len(rows), "file": f.filename})
    return jsonify({"ok": True, "annee": annee, "sheet": meta["sheet"],
                    "rows_imported": len(rows), "rows_skipped": meta["rows_skipped"]})


@app.get("/api/budget/years")
@token_required
def budget_years():
    db = get_db()
    years = budget_module.available_years(db)
    db.close()
    return jsonify({"years": years})


@app.get("/api/budget")
@token_required
def budget_list():
    annee = request.args.get("annee", type=int) or date.today().year
    domaine = request.args.get("domaine") or "parc_auto"
    db = get_db()
    rows = [row_to_dict(r) for r in db.execute(
        "SELECT * FROM budget_plan WHERE annee=? AND domaine=? ORDER BY categorie_std, tache",
        (annee, domaine)).fetchall()]
    db.close()
    return jsonify({"annee": annee, "domaine": domaine, "rows": rows})


@app.get("/api/budget/summary")
@token_required
def budget_summary_route():
    annee = request.args.get("annee", type=int) or date.today().year
    domaine = request.args.get("domaine") or "parc_auto"
    db = get_db()
    summary = budget_module.budget_summary(db, annee, domaine)
    db.close()
    return jsonify(summary)


@app.get("/api/budget/export")
@token_required
def budget_export():
    annee = request.args.get("annee", type=int) or date.today().year
    db = get_db()
    summary = budget_module.budget_summary(db, annee)
    db.close()
    rows = [["Catégorie", "Prévu (FCFA)", "Réalisé (FCFA)", "Écart (FCFA)", "Taux (%)"]]
    for c in summary["categories"]:
        rows.append([c["categorie"], c["prevu"], c["realise"], c["ecart"], c["taux"]])
    rows.append(["TOTAL", summary["total_prevu"], summary["total_realise"], summary["total_ecart"],
                summary["taux_global"]])
    data = io_xlsx.write_xlsx({"Budget vs Réalisé": rows})
    log_action("export", "budget", None, {"annee": annee})
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"nexfleet_budget_{annee}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/budget/pdf")
@token_required
def budget_pdf():
    annee = request.args.get("annee", type=int) or date.today().year
    db = get_db()
    summary = budget_module.budget_summary(db, annee)
    db.close()
    data = pdfgen.budget_report(summary)
    log_action("pdf", "budget", None, {"annee": annee})
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"nexfleet_budget_{annee}.pdf", mimetype="application/pdf")


# ---------------------------------------------------------------- coût total de possession (TCO)
@app.get("/api/tco")
@token_required
def tco_dashboard():
    db = get_db()
    vehicles = [dict(r) for r in db.execute("SELECT * FROM vehicles").fetchall()]
    today_d = date.today()
    items = []
    fleet_total = 0.0
    category_totals = {}

    for v in vehicles:
        maint_rows = [dict(r) for r in db.execute(
            "SELECT type, cout, date FROM maintenance WHERE vehicle_id=?", (v["id"],)).fetchall()]
        vidange_rows = [dict(r) for r in db.execute(
            "SELECT cout, date FROM vidanges WHERE vehicle_id=?", (v["id"],)).fetchall()]
        maint_cost = sum(float(r["cout"] or 0) for r in maint_rows)
        vidange_cost = sum(float(r["cout"] or 0) for r in vidange_rows)
        total_cost = maint_cost + vidange_cost
        fleet_total += total_cost

        for r in maint_rows:
            cat = budget_module.normalize_categorie(r["type"])
            category_totals[cat] = category_totals.get(cat, 0) + float(r["cout"] or 0)
        if vidange_rows:
            category_totals["Vidange"] = category_totals.get("Vidange", 0) + vidange_cost

        km = max(v.get("kilometrage") or 0, 1)
        try:
            created = datetime.strptime((v.get("created_at") or "")[:10], "%Y-%m-%d").date()
            age_months = max(1, (today_d.year - created.year) * 12 + (today_d.month - created.month))
        except (ValueError, TypeError):
            age_months = 1

        items.append({
            "vehicle_id": v["id"], "immatriculation": v["immatriculation"],
            "marque": v["marque"], "modele": v["modele"], "statut": v["statut"],
            "kilometrage": v.get("kilometrage") or 0,
            "maintenance_cost": round(maint_cost, 2), "vidange_cost": round(vidange_cost, 2),
            "total_cost": round(total_cost, 2),
            "cost_per_km": round(total_cost / km, 2),
            "cost_per_month": round(total_cost / age_months, 2),
            "interventions": len(maint_rows) + len(vidange_rows),
        })

    items.sort(key=lambda x: x["total_cost"], reverse=True)

    months = []
    for i in range(11, -1, -1):
        m = (today_d.replace(day=1) - timedelta(days=i * 30)).strftime("%Y-%m")
        months.append(m)
    monthly = {m: 0.0 for m in months}
    for r in db.execute("SELECT date, cout FROM maintenance"):
        key = str(r["date"] or "")[:7]
        if key in monthly:
            monthly[key] += float(r["cout"] or 0)
    for r in db.execute("SELECT date, cout FROM vidanges"):
        key = str(r["date"] or "")[:7]
        if key in monthly:
            monthly[key] += float(r["cout"] or 0)

    db.close()
    return jsonify({
        "vehicles": items,
        "fleet_total_cost": round(fleet_total, 2),
        "fleet_avg_cost": round(fleet_total / len(items), 2) if items else 0,
        "top5": items[:5],
        "category_totals": {k: round(v, 2) for k, v in category_totals.items()},
        "monthly_trend": [{"month": m, "cost": round(monthly[m], 2)} for m in months],
    })


# ---------------------------------------------------------------- assistant intelligent
@app.post("/api/assistant/ask")
@token_required
def assistant_ask():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return err("Question requise.")
    if len(question) > 800:
        return err("Question trop longue (800 caractères max).")
    db = get_db()
    try:
        result = assistant.answer(db, question, user_id=getattr(request, "user_id", None))
    finally:
        db.close()
    log_action("ask", "assistant", None, {"question": question[:200], "source": result.get("source")})
    return jsonify(result)


@app.get("/api/assistant/history")
@token_required
def assistant_history():
    db = get_db()
    try:
        uid = getattr(request, "user_id", None)
        if not uid:
            return jsonify([])
        rows = db.execute(
            "SELECT role, content, created_at FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (uid,)).fetchall()
        return jsonify([dict(r) for r in reversed(rows)])
    finally:
        db.close()


@app.delete("/api/assistant/history")
@token_required
def assistant_clear_history():
    db = get_db()
    try:
        uid = getattr(request, "user_id", None)
        if uid:
            db.execute("DELETE FROM chat_history WHERE user_id=?", (uid,))
            db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ---------------------------------------------------------------- notifications par e-mail
@app.post("/api/notify/send-digest")
@token_required
@admin_required
def notify_send_digest():
    try:
        result = notify.send_digest_now()
    except ValueError as e:
        return err(str(e))
    except Exception as e:
        return err(f"Envoi impossible : {e}")
    log_action("send", "notify_digest", None, {"recipients": result.get("recipients")})
    return jsonify(result)


@app.get("/api/notify/config")
@token_required
@admin_required
def notify_config_route():
    cfg = notify.notify_config()
    cfg.pop("smtp_pass", None)
    cfg["configured"] = notify.is_configured()
    return jsonify(cfg)


# ---------------------------------------------------------------- sauvegarde
@app.get("/api/backup")
@token_required
@admin_required
def backup_db():
    src = sqlite3.connect(DB_PATH)
    tmp = os.path.join(tempfile.gettempdir(),
                       f"nf_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db")
    dst = sqlite3.connect(tmp)
    src.backup(dst)
    dst.close()
    src.close()
    with open(tmp, "rb") as f:
        data = f.read()
    try:
        os.remove(tmp)
    except OSError:
        pass
    log_action("export", "backup")
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"nexfleet_sauvegarde_{date.today().isoformat()}.db",
                     mimetype="application/octet-stream")


# ---------------------------------------------------------------- rapport comparatif mensuel
@app.get("/api/reports/monthly/pdf")
@token_required
def monthly_report_pdf():
    db = get_db()
    today_d = date.today()
    months = []
    for i in range(11, -1, -1):
        m = (today_d.replace(day=1) - timedelta(days=i * 31)).strftime("%Y-%m")
        veh_new = db.execute("SELECT COUNT(*) AS n FROM vehicles WHERE substr(created_at,1,7)=?",
                             (m,)).fetchone()["n"]
        ctrl = db.execute("SELECT COUNT(*) AS n FROM controls WHERE substr(date,1,7)=?",
                          (m,)).fetchone()["n"]
        mnt = db.execute("SELECT COALESCE(SUM(cout),0) AS n FROM maintenance WHERE substr(date,1,7)=?",
                         (m,)).fetchone()["n"]
        months.append({"month": m, "vehicles_new": veh_new, "controls": ctrl,
                       "maintenance_cost": float(mnt)})
    db.close()
    data = pdfgen.monthly_report(months)
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"rapport_mensuel_{today_d.isoformat()}.pdf",
                     mimetype="application/pdf")


# ---------------------------------------------------------------- PDF
@app.get("/api/vehicles/<int:vid>/pdf")
@token_required
def vehicle_pdf(vid):
    db = get_db()
    v = db.execute("SELECT * FROM vehicles WHERE id=?", (vid,)).fetchone()
    if v is None:
        db.close()
        return err("Véhicule introuvable.", 404)
    last = db.execute("SELECT * FROM controls WHERE vehicle_id=? ORDER BY date DESC LIMIT 1",
                      (vid,)).fetchone()
    driver_name = None
    if last and last["driver_id"]:
        dr = db.execute("SELECT nom, prenom FROM drivers WHERE id=?", (last["driver_id"],)).fetchone()
        if dr:
            driver_name = f"{dr['prenom']} {dr['nom']}"
    items = parse_items(last["items"] if last else {})
    db.close()
    data = pdfgen.control_pdf(
        row_to_dict(v), driver_name, items,
        last["resultat"] if last else "En cours",
        last["notes"] if last else "",
        last["type"] if last else "Contrôle technique",
    )
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name=f"Fiche_controle_{v['immatriculation']}.pdf",
                     mimetype="application/pdf")


@app.get("/api/parc/pdf")
@token_required
def parc_pdf():
    db = get_db()
    rows = db.execute("SELECT * FROM vehicles ORDER BY marque").fetchall()
    s = {}
    s["total"] = len(rows)
    s["en_service"] = sum(1 for r in rows if "service" in (r["statut"] or "").lower())
    s["en_maintenance"] = sum(1 for r in rows if "maintenance" in (r["statut"] or "").lower())
    s["en_panne"] = sum(1 for r in rows if "panne" in (r["statut"] or "").lower())
    s["drivers"] = db.execute("SELECT COUNT(*) AS n FROM drivers").fetchone()["n"]
    months = []
    for i in range(5, -1, -1):
        m = (date.today().replace(day=1) - timedelta(days=i * 31)).strftime("%Y-%m")
        n = db.execute("SELECT COUNT(*) AS n FROM controls WHERE substr(date,1,7)=?", (m,)).fetchone()["n"]
        months.append({"month": m, "count": n})

    m_rows = [dict(r) for r in db.execute(
        """SELECT m.id, m.type, m.date, m.cout, m.garage, m.notes,
                  v.immatriculation, v.marque, v.modele
           FROM maintenance m JOIN vehicles v ON v.id = m.vehicle_id
           ORDER BY m.date DESC, m.id DESC""").fetchall()]
    by_veh = {}
    for m in m_rows:
        k = m["immatriculation"]
        b = by_veh.setdefault(k, {"immatriculation": k, "marque": m["marque"],
                                  "modele": m["modele"], "count": 0, "cout": 0.0})
        b["count"] += 1
        b["cout"] += float(m["cout"] or 0)

    vg_rows = [dict(r) for r in db.execute(
        """SELECT vg.*, v.immatriculation, v.marque, v.modele, v.kilometrage
           FROM vidanges vg JOIN vehicles v ON v.id = vg.vehicle_id
           ORDER BY vg.date DESC, vg.id DESC""").fetchall()]
    vg_by_veh = {}
    for g in vg_rows:
        k = g["immatriculation"]
        b = vg_by_veh.setdefault(k, {"immatriculation": k, "marque": g["marque"],
                                     "modele": g["modele"], "count": 0, "cout": 0.0})
        b["count"] += 1
        b["cout"] += float(g["cout"] or 0)
    db.close()
    data = pdfgen.parc_report(
        [row_to_dict(r) for r in rows], s, months,
        maintenance=m_rows,
        maintenance_by_vehicle=sorted(by_veh.values(), key=lambda x: -x["cout"]),
        maintenance_total=sum(v["cout"] for v in by_veh.values()),
        vidanges=vg_rows,
        vidanges_by_vehicle=sorted(vg_by_veh.values(), key=lambda x: -x["cout"]),
        vidanges_total=sum(v["cout"] for v in vg_by_veh.values()),
    )
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name="Rapport_du_parc_automobile.pdf",
                     mimetype="application/pdf")


# ---------------------------------------------------------------- données de démo
@app.post("/api/demo")
@token_required
@admin_required
def seed_demo():
    db = get_db()
    if db.execute("SELECT COUNT(*) AS n FROM vehicles").fetchone()["n"] > 0:
        db.close()
        return err("Le parc contient déjà des données.", 409)

    d = date.today()
    def shift(days):
        return (d + timedelta(days=days)).isoformat()

    marques = [
        ("AB-123-CD", "Renault", "Master", 2021, "Utilitaire", "Diesel", 58400, 25, 40, 90, "En service", "Dépôt Paris-Nord", "VF1MA2E0H00000001", "F4R710", 120, 49.283, 2.417),
        ("DE-456-FG", "Peugeot", "Expert", 2022, "Utilitaire", "Diesel", 42100, 120, 15, -12, "En service", "Agence Lyon", "VF3MCFYHZKS000002", "DW10FD", 130, 45.758, 4.835),
        ("GH-789-IJ", "Citroën", "Jumper", 2019, "Camion", "Diesel", 120350, -3, -20, 60, "En maintenance", "Entrepôt Marseille", "VF7YCNMFBKS000003", "2.0 HDi", 160, 43.297, 5.369),
        ("KL-012-MN", "Ford", "Transit", 2020, "Utilitaire", "Essence", 88900, 200, 75, 45, "En service", "Dépôt Paris-Nord", "WF0YXXWVKYKD000004", "2.0 EcoBoost", 170, 49.290, 2.430),
        ("OP-345-QR", "Toyota", "Corolla", 2023, "Berline", "Hybride", 15800, 300, 210, 330, "En service", "Direction générale", "SB1JZ3HE300000005", "2ZR-FXE", 122, 49.275, 2.410),
        ("ST-678-UV", "Volkswagen", "Golf", 2021, "Berline", "Essence", 34200, 90, 55, 140, "En panne", "Agence Bordeaux", "WVWZZZ3CZNE000006", "EA211", 150, 44.838, -0.579),
        ("WX-901-YZ", "Mercedes", "Sprinter", 2018, "Camion", "Diesel", 187500, 10, 35, -45, "En service", "Entrepôt Marseille", "WDAPF4EB0J5000007", "OM651", 163, 43.310, 5.390),
        ("AA-234-BB", "Dacia", "Duster", 2022, "4x4", "Diesel", 41200, 160, 95, 60, "En service", "Site Nantes", "UU1HJD4H3KM000008", "dCi 115", 115, 47.218, -1.553),
        ("CC-567-DD", "Iveco", "Daily", 2020, "Camion", "Diesel", 132000, 70, 25, 30, "En service", "Site Toulouse", "ZAR96DTL0L2000009", "F1AFL411", 160, 43.604, 1.444),
        ("EE-890-FF", "Tesla", "Model 3", 2023, "Berline", "Électrique", 22100, 365, 180, 95, "En service", "Direction générale", "5YJ3E7EB3NF000010", "PMSM", 283, 49.280, 2.425),
    ]
    for m in marques:
        db.execute(
            "INSERT INTO vehicles (immatriculation, marque, modele, annee, type, carburant, kilometrage, vignette_exp, assurance_exp, ctrl_tech_exp, statut, affectation, num_chassis, num_moteur, cv, lat, lng, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (m[0], m[1], m[2], m[3], m[4], m[5], m[6], shift(m[7]), shift(m[8]), shift(m[9]), m[10], m[11], m[12], m[13], m[14], m[15], m[16], now()))

    drivers = [("Diallo", "Awa", "MAT-001", "a.diallo@nexfleet.fr", "06 12 34 56 78", "B", shift(900), shift(700)),
               ("Martin", "Lucas", "MAT-002", "l.martin@nexfleet.fr", "06 98 76 54 32", "B", shift(400), shift(300)),
               ("Nguyen", "Sophie", "MAT-003", "s.nguyen@nexfleet.fr", "07 11 22 33 44", "C", shift(250), shift(180)),
               ("Kone", "Issa", "MAT-004", "i.kone@nexfleet.fr", "07 55 66 77 88", "B", shift(-15), shift(-30))]
    for drow in drivers:
        db.execute("INSERT INTO drivers (nom, prenom, matricule, email, telephone, permis, permis_exp, cni_exp, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                   (*drow, now()))

    items_ok = {name: "Conforme" for name in ("Carrosserie et état extérieur", "Pneumatiques et pression")}
    items_warn = {**items_ok, "Freins et plaquettes": "À surveiller"}
    for i in range(18):
        db.execute("INSERT INTO controls (vehicle_id, driver_id, date, type, resultat, notes, items, created_at) VALUES (?,?,?,?,?,?,?,?)",
                   ((i % 10) + 1, (i % 4) + 1, shift(-(i * 11) % 160),
                    "Contrôle technique" if i % 3 else "Contrôle d'usage",
                    "Conforme" if i % 4 else "À surveiller",
                    "Aucune anomalie." if i % 4 else "Prévoir plaquettes avant la prochaine révision.",
                    json.dumps(items_warn if i % 4 == 0 else items_ok, ensure_ascii=False), now()))

    for i in range(12):
        db.execute("INSERT INTO maintenance (vehicle_id, type, date, cout, garage, notes, created_at) VALUES (?,?,?,?,?,?,?)",
                   ((i % 10) + 1, ["Révision", "Pneus", "Freins", "Vidange", "Électronique"][i % 5],
                    shift(-(i * 23) % 200), (90 + i * 40), "Garage NexAUTO",
                    "Maintenance préventive.", now()))

    for i in range(1, 11):
        base = marques[i - 1][6]
        for j, delta in enumerate((60, 30, 0)):
            db.execute("INSERT INTO odometer (vehicle_id, date, kilometres, note, created_at) VALUES (?,?,?,?,?)",
                       (i, shift(-delta), base - delta * 210, "Relevé périodique", now()))
        db.execute("INSERT INTO tires (vehicle_id, position, marque, taille, etat, date_montage, note, created_at) VALUES (?,?,?,?,?,?,?,?)",
                   (i, "AVG", "Michelin", "225/70 R16", "Bon", shift(-120), "Train avant", now()))
        db.execute("INSERT INTO tires (vehicle_id, position, marque, taille, etat, date_montage, note, created_at) VALUES (?,?,?,?,?,?,?,?)",
                   (i, "ARD", "Michelin", "225/70 R16", "À surveiller", shift(-300), "Usure légère", now()))
        db.execute("INSERT INTO documents (vehicle_id, label, filename, stored, created_at) VALUES (?,?,?,?,?)",
                   (i, "Carte grise", "carte_grise.pdf", "/uploads/demo_cg.txt", now()))
        db.execute("INSERT INTO vidanges (vehicle_id, date, km, huile, quantite, filtre, cout, garage, notes, prochaine_km, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (i, shift(-50), base - 900, "10W-40", 7.0, 1, 65 + i * 5,
                    "Garage NexAUTO", "Vidange périodique.", base + 9100, now()))

    demo_file = os.path.join(UPLOAD_DIR, "demo_cg.txt")
    if not os.path.isfile(demo_file):
        try:
            with open(demo_file, "w", encoding="utf-8") as f:
                f.write("Document de démonstration — carte grise NexFleet.\n")
        except OSError:
            pass

    db.commit()
    db.close()
    log_action("demo", "parc", None, {"vehicles": 10, "drivers": 4})
    return jsonify({"ok": True, "message": "Données de démonstration chargées."})


# ---------------------------------------------------------------- journal d'activité
@app.get("/api/audit")
@token_required
def audit():
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(max(int(request.args.get("per_page", 50)), 5), 200)
    except (ValueError, TypeError):
        per_page = 50
    action = (request.args.get("action") or "").strip()
    username = (request.args.get("username") or "").strip()
    search = (request.args.get("search") or "").strip()
    base = "FROM audit_log WHERE 1=1"
    params = []
    if action:
        base += " AND action = ?"
        params.append(action)
    if username:
        base += " AND username = ?"
        params.append(username)
    if search:
        base += " AND (entity LIKE ? OR details LIKE ? OR username LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n " + base, params).fetchone()["n"]
    rows = db.execute(
        "SELECT * " + base + " ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page]).fetchall()
    summary = {r["action"]: r["n"] for r in db.execute(
        "SELECT action, COUNT(*) AS n FROM audit_log GROUP BY action ORDER BY n DESC")}
    users = [r["username"] for r in db.execute(
        "SELECT DISTINCT username FROM audit_log WHERE username IS NOT NULL AND username != '' ORDER BY username")]
    db.close()
    return jsonify({
        "events": [row_to_dict(r) for r in rows],
        "total": total, "page": page, "per_page": per_page,
        "pages": max(ceil(total / per_page) if per_page else 0, 1),
        "summary": summary, "users": users,
    })


@app.get("/api/notifications")
@token_required
def notifications():
    alerts = all_alerts()
    db = get_db()
    events = [dict(r) for r in db.execute(
        "SELECT id, username, action, entity, details, created_at FROM audit_log ORDER BY id DESC LIMIT 8").fetchall()]
    db.close()
    for e in events:
        try:
            e["details"] = json.loads(e["details"]) if e["details"] else {}
        except (ValueError, TypeError):
            e["details"] = {}
    return jsonify({
        "alerts": alerts,
        "danger_count": sum(1 for a in alerts if a["level"] == "danger"),
        "warning_count": sum(1 for a in alerts if a["level"] == "warning"),
        "events": events,
    })


# ---------------------------------------------------------------- import / export
@app.get("/api/import/template")
@token_required
def import_template():
    sheets = {
        "Véhicules": [
            ["Immatriculation", "Marque", "Modèle", "Année", "Type", "Carburant",
             "Kilométrage", "Statut", "Direction", "Affectation", "Échéance vignette", "Échéance assurance",
             "Échéance contrôle technique", "N° Châssis", "N° Moteur", "CV"],
            ["AB-123-CD", "Renault", "Master", 2021, "Utilitaire", "Diesel",
             58400, "En service", "Direction Générale", "Dépôt Paris-Nord", "2026-09-01", "2026-11-15", "2027-03-10",
             "VF1MA2E0H12345678", "F4R710", 120],
        ],
        "Conducteurs": [
            ["Nom", "Prénom", "Matricule", "Email", "Téléphone", "Permis", "Validité permis", "Expiration CNI"],
            ["Diallo", "Awa", "MAT-001", "a.diallo@nexfleet.fr", "06 12 34 56 78", "B", "2029-05-20", "2028-12-01"],
        ],
        "Contrôles": [
            ["Immatriculation", "Conducteur", "Date", "Type", "Résultat", "Observations"],
            ["AB-123-CD", "Awa Diallo", "2026-01-12", "Contrôle technique", "Conforme", "Aucune anomalie."],
        ],
        "Maintenance": [
            ["Immatriculation", "Type", "Date", "Coût (FCFA)", "Garage", "Observations"],
            ["AB-123-CD", "Révision", "2026-02-01", 180000, "Garage NexAUTO", "Vidange + filtres."],
        ],
        "Vidanges": [
            ["Immatriculation", "Date", "Km", "Huile", "Quantité (L)", "Filtre",
             "Coût (FCFA)", "Garage", "Observations", "Prochaine vidange (km)"],
            ["AB-123-CD", "2026-02-01", 58400, "10W-40", 7.0, "Oui",
             75000, "Garage NexAUTO", "Vidange périodique.", 68400],
        ],
    }
    data = io_xlsx.write_xlsx(sheets)
    log_action("template", "import")
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name="nexfleet_modele_import.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.post("/api/import")
@token_required
@admin_required
def do_import():
    f = request.files.get("file")
    if f is None or not f.filename:
        return err("Aucun fichier fourni.")
    raw = f.read()
    if not raw:
        return err("Fichier vide.")
    name = (f.filename or "").lower()
    try:
        if name.endswith(".xlsx"):
            result = imp_exp.import_workbook(raw)
        elif name.endswith(".csv"):
            text = raw.decode("utf-8-sig", errors="replace")
            import csv
            sample = text.splitlines()[:10]
            dialect = csv.Sniffer().sniff("\n".join(sample), delimiters=";,") if sample else None
            rows = list(csv.reader(text.splitlines(), dialect or csv.excel))
            result = imp_exp.import_sheets({"Import": rows})
        else:
            return err("Format non supporté : utilisez un fichier .xlsx ou .csv.")
    except ValueError as e:
        return err(str(e))
    except Exception as e:
        return err(f"Import impossible : {e}")
    log_action("import", "parc", None, {
        "file": f.filename,
        "created": result["total_created"], "updated": result["total_updated"],
        "errors": result["total_errors"],
    })
    return jsonify({"ok": True, **result})


@app.post("/api/import/analyze")
@token_required
@admin_required
def analyze_import():
    f = request.files.get("file")
    if f is None or not f.filename:
        return err("Aucun fichier fourni.")
    raw = f.read()
    if not raw:
        return err("Fichier vide.")
    analysis, error = imp_exp.analyze_file(raw, f.filename)
    if error:
        return err(error)
    return jsonify({"ok": True, **analysis})


@app.get("/api/export")
@token_required
def do_export():
    fmt = (request.args.get("format") or "xlsx").lower()
    entity = (request.args.get("entity") or "all").lower()
    if fmt == "csv":
        sheets = imp_exp.export_sheets()
        key = {"vehicles": "Véhicules", "drivers": "Conducteurs",
               "controls": "Contrôles", "maintenance": "Maintenance",
               "vidanges": "Vidanges"}.get(entity, "Véhicules")
        data = io_xlsx.write_csv(sheets.get(key, [["Aucune donnée"]]))
        log_action("export", "parc", None, {"format": "csv", "entity": key})
        return send_file(io.BytesIO(data), as_attachment=True,
                         download_name=f"nexfleet_{key.lower()}.csv", mimetype="text/csv")
    sheets = imp_exp.export_sheets()
    if entity != "all":
        key = {"vehicles": "Véhicules", "drivers": "Conducteurs",
               "controls": "Contrôles", "maintenance": "Maintenance",
               "vidanges": "Vidanges"}.get(entity)
        if key:
            sheets = {key: sheets.get(key, [["Aucune donnée"]])}
    data = io_xlsx.write_xlsx(sheets)
    log_action("export", "parc", None, {"format": "xlsx"})
    return send_file(io.BytesIO(data), as_attachment=True,
                     download_name="nexfleet_parc.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------------------------------------------------------------- détail véhicule
@app.get("/api/vehicles/<int:vid>/detail")
@token_required
def vehicle_detail(vid):
    db = get_db()
    v = db.execute("SELECT * FROM vehicles WHERE id=?", (vid,)).fetchone()
    if v is None:
        db.close()
        return err("Véhicule introuvable.", 404)
    v = dict(v)
    v["alerts"] = vehicle_alerts(v) + vidange_km_alert(db, v)
    controls = [dict(r) for r in db.execute(
        """SELECT c.*, d.nom AS d_nom, d.prenom AS d_prenom
           FROM controls c LEFT JOIN drivers d ON d.id = c.driver_id
           WHERE c.vehicle_id=? ORDER BY c.date DESC LIMIT 10""", (vid,)).fetchall()]
    maintenance = [dict(r) for r in db.execute(
        "SELECT * FROM maintenance WHERE vehicle_id=? ORDER BY date DESC LIMIT 10", (vid,)).fetchall()]
    vidanges = [dict(r) for r in db.execute(
        "SELECT * FROM vidanges WHERE vehicle_id=? ORDER BY date DESC, id DESC LIMIT 10", (vid,)).fetchall()]
    history = vehicle_history(db, vid)
    db.close()
    for c in controls:
        c["items"] = parse_items(c.get("items"))
    total_spent = sum(h["cost"] for h in history)
    return jsonify({
        "vehicle": v,
        "controls": controls,
        "maintenance": maintenance,
        "vidanges": vidanges,
        "history": history,
        "total_spent": total_spent,
    })


# ---------------------------------------------------------------- GPS / localisation
@app.get("/api/vehicles/locations")
@token_required
def vehicle_locations():
    db = get_db()
    rows = db.execute(
        "SELECT id, immatriculation, marque, modele, statut, lat, lng, affectation FROM vehicles"
    ).fetchall()
    db.close()
    vehicles = []
    for r in rows:
        v = dict(r)
        vehicles.append(v)
    return jsonify({"vehicles": vehicles})


@app.put("/api/vehicles/<int:vid>/location")
@token_required
def update_vehicle_location(vid):
    data = request.get_json(silent=True) or {}
    lat = _safe_float(data.get("lat"))
    lng = _safe_float(data.get("lng"))
    if lat is None or lng is None:
        return err("Coordonnées GPS invalides (lat, lng requis).")
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return err("Coordonnées GPS hors limites.")
    db = get_db()
    cur = db.execute("UPDATE vehicles SET lat=?, lng=? WHERE id=?", (lat, lng, vid))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        return err("Véhicule introuvable.", 404)
    log_action("update", "vehicle_location", vid, {"lat": lat, "lng": lng})
    return jsonify({"ok": True})


# ---------------------------------------------------------------- frontend statique
@app.get("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def serve_static(path):
    if os.path.isfile(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return err("Ressource introuvable.", 404)


# ---------------------------------------------------------------- global
@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Ressource introuvable."}), 404


@app.errorhandler(500)
def server_error(_):
    return jsonify({"error": "Erreur interne du serveur."}), 500


if __name__ == "__main__":
    _host = os.environ.get("HOST", "0.0.0.0")
    _port = int(os.environ.get("PORT", "5000"))
    app.run(host=_host, port=_port, debug=False)
