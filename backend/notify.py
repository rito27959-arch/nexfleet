# -*- coding: utf-8 -*-
"""Notifications automatiques par e-mail (échéances, budget, maintenance
prédictive) + planificateur léger en arrière-plan.

Zéro dépendance externe : smtplib + email (bibliothèque standard).
"""

import smtplib
import threading
import time
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from db import get_db, get_setting, now, set_setting

CHECK_INTERVAL_SECONDS = 30 * 60  # vérifie toutes les 30 minutes si un digest est dû
_scheduler_started = False


def _truthy(v):
    return str(v or "0").strip() in ("1", "true", "True", "on", "yes")


def notify_config():
    try:
        hour = int(get_setting("notify_hour", "7") or 7)
    except (ValueError, TypeError):
        hour = 7
    try:
        smtp_port = int(get_setting("smtp_port", "587") or 587)
    except (ValueError, TypeError):
        smtp_port = 587
    return {
        "enabled": _truthy(get_setting("notify_enabled", "0")),
        "emails": [e.strip() for e in (get_setting("notify_emails", "") or "").split(",") if e.strip()],
        "hour": hour,
        "smtp_host": get_setting("smtp_host", "") or "",
        "smtp_port": smtp_port,
        "smtp_user": get_setting("smtp_user", "") or "",
        "smtp_pass": get_setting("smtp_pass", "") or "",
        "smtp_from": get_setting("smtp_from", "") or get_setting("smtp_user", "") or "",
        "smtp_tls": _truthy(get_setting("smtp_tls", "1")),
        "last_digest_sent": get_setting("last_digest_sent", "") or "",
    }


def is_configured(cfg=None):
    cfg = cfg or notify_config()
    return bool(cfg["smtp_host"] and cfg["smtp_user"] and cfg["smtp_from"] and cfg["emails"])


# ---------------------------------------------------------------- contenu du digest
def build_digest(db):
    """Construit le contenu du digest quotidien à partir des données réelles
    du parc (échéances, budget, maintenance prédictive)."""
    import app as app_module  # import différé pour éviter les imports circulaires

    alerts = app_module.all_alerts()
    danger = [a for a in alerts if a["level"] == "danger"]
    warning = [a for a in alerts if a["level"] == "warning"]

    forecast = app_module.compute_maintenance_forecast(db)
    soon = [f for f in forecast if f["level"] in ("danger", "warning")][:10]

    import budget as budget_module
    annee = date.today().year
    summary = budget_module.budget_summary(db, annee)
    budget_alerts = summary["alerts"]

    lines_txt = [f"NexFleet — Rapport quotidien du {date.today().strftime('%d/%m/%Y')}", ""]
    html_parts = [f"<h2 style='font-family:Arial'>NexFleet — Rapport quotidien</h2>"
                  f"<p style='color:#64748b;font-family:Arial'>{date.today().strftime('%d/%m/%Y')}</p>"]

    def section(title, items, fmt):
        if not items:
            return
        lines_txt.append(f"\n{title} ({len(items)})")
        html_parts.append(f"<h3 style='font-family:Arial;color:#1e293b'>{title} ({len(items)})</h3><ul style='font-family:Arial'>")
        for it in items:
            txt, html_line = fmt(it)
            lines_txt.append(f"  - {txt}")
            html_parts.append(f"<li>{html_line}</li>")
        html_parts.append("</ul>")

    section("⛔ Échéances dépassées", danger,
             lambda a: (f"{a.get('vehicle', '')} ({a.get('immatriculation', '')}) — {a['msg']}",
                        f"<b>{a.get('vehicle', '')}</b> ({a.get('immatriculation', '')}) — {a['msg']}"))
    section("⚠️ Échéances à venir (30 jours)", warning,
             lambda a: (f"{a.get('vehicle', '')} ({a.get('immatriculation', '')}) — {a['msg']}",
                        f"{a.get('vehicle', '')} ({a.get('immatriculation', '')}) — {a['msg']}"))
    section("🔧 Maintenance prédictive à prévoir", soon,
             lambda f: (f"{f['marque']} {f['modele']} ({f['immatriculation']}) — {f['type']} prévue vers le {f['date_due']}",
                        f"{f['marque']} {f['modele']} ({f['immatriculation']}) — {f['type']} prévue vers le <b>{f['date_due']}</b>"))
    section("💰 Catégories budgétaires en alerte", budget_alerts,
             lambda b: (f"{b['categorie']} : réalisé {b['realise']:,.0f} FCFA / prévu {b['prevu']:,.0f} FCFA ({b['taux']}%)",
                        f"<b>{b['categorie']}</b> : réalisé {b['realise']:,.0f} FCFA / prévu {b['prevu']:,.0f} FCFA "
                        f"(<b style='color:{'#ef4444' if b['level']=='danger' else '#f59e0b'}'>{b['taux']}%</b>)"))

    if not (danger or warning or soon or budget_alerts):
        lines_txt.append("\nAucune alerte : le parc est à jour. ✅")
        html_parts.append("<p style='font-family:Arial;color:#10b981'>Aucune alerte : le parc est à jour. ✅</p>")

    subject = f"NexFleet — {len(danger)} urgence(s), {len(warning)} à venir, {len(budget_alerts)} alerte(s) budget"
    text = "\n".join(lines_txt)
    html = "<div style='font-family:Arial'>" + "".join(html_parts) + \
           "<p style='color:#94a3b8;font-size:12px'>Envoyé automatiquement par NexFleet.</p></div>"
    return subject, text, html


# ---------------------------------------------------------------- envoi SMTP
def send_email(subject, text, html, recipients, cfg=None):
    cfg = cfg or notify_config()
    if not is_configured(cfg):
        raise ValueError("Configuration SMTP incomplète (hôte, utilisateur, expéditeur et destinataires requis).")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["smtp_from"]
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=20) as server:
        if cfg["smtp_tls"]:
            server.starttls()
        if cfg["smtp_user"]:
            server.login(cfg["smtp_user"], cfg["smtp_pass"])
        server.sendmail(cfg["smtp_from"], recipients, msg.as_string())


def send_digest_now():
    db = get_db()
    try:
        cfg = notify_config()
        subject, text, html = build_digest(db)
        send_email(subject, text, html, cfg["emails"], cfg)
        set_setting("last_digest_sent", date.today().isoformat())
        return {"ok": True, "recipients": len(cfg["emails"]), "subject": subject}
    finally:
        db.close()


# ---------------------------------------------------------------- planificateur
def _tick():
    while True:
        try:
            cfg = notify_config()
            if cfg["enabled"] and is_configured(cfg):
                today_iso = date.today().isoformat()
                if cfg["last_digest_sent"] != today_iso and datetime.now().hour >= cfg["hour"]:
                    send_digest_now()
        except Exception:
            pass  # le planificateur ne doit jamais interrompre le serveur
        time.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True
    t = threading.Thread(target=_tick, daemon=True, name="nexfleet-notify-scheduler")
    t.start()
