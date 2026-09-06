# -*- coding: utf-8 -*-
"""Assistant intelligent NexFleet — v2 améliorée.

Améliorations :
- Mémoire conversationnelle (chat_history en DB, 20 derniers échanges envoyés au LLM)
- RAG : contexte ciblé selon la question (pas tout le parc à chaque fois)
- Règles locales enrichies (direction, recherche par immatriculation, stats, etc.)
- System prompt enrichi avec la liste des véhicules et conducteurs
"""

import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

from db import get_db, get_setting

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4.1-mini"


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _any(text, *keywords):
    return any(kw in text for kw in keywords)


def _fmt_fcfa(n):
    try:
        return f"{round(float(n)):,}".replace(",", " ") + " FCFA"
    except (ValueError, TypeError):
        return "0 FCFA"


# ---------------------------------------------------------------- mémoire
def _get_history(db, user_id, limit=20):
    """Récupère les derniers échanges pour la mémoire conversationnelle."""
    if not user_id:
        return []
    rows = db.execute(
        "SELECT role, content FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _save_history(db, user_id, role, content):
    """Enregistre un message dans l'historique."""
    if not user_id:
        return
    from db import now
    db.execute("INSERT INTO chat_history (user_id, role, content, created_at) VALUES (?,?,?,?)",
               (user_id, role, content, now()))
    db.commit()
    cutoff = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds")
    db.execute("DELETE FROM chat_history WHERE created_at < ? AND user_id=?", (cutoff, user_id))
    db.commit()


# ---------------------------------------------------------------- RAG : contexte ciblé
def _extract_entities(text):
    """Extrait entités de la question : immatriculation, marque, modèle, direction, conducteur."""
    t = _norm(text)
    entities = {}
    imm_match = re.search(r'\b([A-Z]{2}[\s\-]?\d{2,4}[\s\-]?[A-Z]{2,4})\b', text.upper())
    if imm_match:
        entities["immatriculation"] = imm_match.group(1).strip()
    directions = {"direction generale", "drh", "daf", "drh", "dga", "dgi", "dg", "direction technique",
                  "direction financiere", "direction administrative", "direction commerciale",
                  "direction des ressources humaines", "direction generale"}
    for d in directions:
        if d in t:
            entities["direction"] = d
            break
    marques = {"renault", "peugeot", "citroen", "toyota", "nissan", "mercedes", "volkswagen",
               "ford", "hyundai", "kia", "bmw", "opel", "fiat", "hino", "iveco", "man",
               "mazda", "suzuki", "honda", "mitsubishi", "daf", "scania", "renault trucks"}
    for m in marques:
        if m in t:
            entities["marque"] = m
            break
    if _any(t, "conducteur", "chauffeur", "conductrice"):
        entities["ask_driver"] = True
    if _any(t, "direction"):
        entities["ask_direction"] = True
    return entities


def gather_context(db):
    """Extrait un instantané compact de l'état du parc."""
    from app import all_alerts, compute_maintenance_forecast
    import budget as budget_module

    stats_rows = dict(
        total=db.execute("SELECT COUNT(*) n FROM vehicles").fetchone()["n"],
        en_service=db.execute("SELECT COUNT(*) n FROM vehicles WHERE statut='En service'").fetchone()["n"],
        en_panne=db.execute("SELECT COUNT(*) n FROM vehicles WHERE statut LIKE '%panne%'").fetchone()["n"],
        en_maintenance=db.execute("SELECT COUNT(*) n FROM vehicles WHERE statut LIKE '%maintenance%'").fetchone()["n"],
        drivers=db.execute("SELECT COUNT(*) n FROM drivers").fetchone()["n"],
    )
    alerts = all_alerts()
    forecast = compute_maintenance_forecast(db)
    annee = date.today().year
    budget = budget_module.budget_summary(db, annee)

    top_cost = [dict(r) for r in db.execute(
        """SELECT v.immatriculation, v.marque, v.modele,
                  COALESCE(SUM(m.cout),0)+COALESCE((SELECT SUM(cout) FROM vidanges vg WHERE vg.vehicle_id=v.id),0) AS total
           FROM vehicles v LEFT JOIN maintenance m ON m.vehicle_id=v.id
           GROUP BY v.id ORDER BY total DESC LIMIT 5""")]

    return {
        "date_du_jour": date.today().isoformat(),
        "parc": stats_rows,
        "alertes_urgentes": [a for a in alerts if a["level"] == "danger"][:15],
        "alertes_a_venir": [a for a in alerts if a["level"] == "warning"][:15],
        "maintenance_predictive_proche": [f for f in forecast if f["level"] in ("danger", "warning")][:15],
        "budget_annee": annee,
        "budget_total_prevu_fcfa": budget["total_prevu"],
        "budget_total_realise_fcfa": budget["total_realise"],
        "budget_categories_en_alerte": budget["alerts"],
        "vehicules_plus_couteux": top_cost,
    }


def _rag_context(db, question, entities):
    """Construit un contexte RAG ciblé selon la question."""
    ctx = gather_context(db)

    if entities.get("immatriculation"):
        imm = entities["immatriculation"]
        veh = db.execute("SELECT * FROM vehicles WHERE immatriculation LIKE ?",
                         (f"%{imm}%",)).fetchone()
        if veh:
            ctx["vehicule_recherche"] = dict(veh)
            maint = [dict(r) for r in db.execute(
                "SELECT * FROM maintenance WHERE vehicle_id=? ORDER BY date DESC LIMIT 5", (veh["id"],)).fetchall()]
            ctx["maintenance_vehicule"] = maint
            vg = [dict(r) for r in db.execute(
                "SELECT * FROM vidanges WHERE vehicle_id=? ORDER BY date DESC LIMIT 5", (veh["id"],)).fetchall()]
            ctx["vidanges_vehicule"] = vg
            ctrls = [dict(r) for r in db.execute(
                "SELECT * FROM controls WHERE vehicle_id=? ORDER BY date DESC LIMIT 5", (veh["id"],)).fetchall()]
            ctx["controles_vehicule"] = ctrls
            tires = [dict(r) for r in db.execute(
                "SELECT * FROM tires WHERE vehicle_id=?", (veh["id"],)).fetchall()]
            ctx["pneus_vehicule"] = tires

    if entities.get("direction"):
        d = entities["direction"]
        vehs = [dict(r) for r in db.execute(
            "SELECT immatriculation, marque, modele, statut, affectation FROM vehicles WHERE direction LIKE ?",
            (f"%{d}%",)).fetchall()]
        ctx["vehicules_direction"] = vehs

    if entities.get("marque"):
        m = entities["marque"]
        vehs = [dict(r) for r in db.execute(
            "SELECT immatriculation, modele, annee, statut, kilometrage FROM vehicles WHERE marque LIKE ?",
            (f"%{m}%",)).fetchall()]
        ctx["vehicules_marque"] = vehs

    if entities.get("ask_driver"):
        drivers = [dict(r) for r in db.execute(
            "SELECT nom, prenom, permis, permis_exp, cni_exp FROM drivers ORDER BY nom LIMIT 30").fetchall()]
        ctx["conducteurs"] = drivers

    vehs_all = db.execute(
        "SELECT immatriculation, marque, modele, direction, statut FROM vehicles ORDER BY marque").fetchall()
    ctx["liste_vehicules"] = [dict(v) for v in vehs_all]

    return ctx


# ---------------------------------------------------------------- règles locales
def _rule_answers(text, ctx):
    p = ctx["parc"]

    if _any(text, "bonjour", "salut", "bonsoir", "hello", "coucou", "salutation") and len(text) < 40:
        return ("Bonjour ! Je suis l'assistant NexFleet. Posez-moi une question sur votre parc : "
                "échéances, budget, coûts, maintenance, véhicules, conducteurs, directions...")

    if _any(text, "merci", "super", "parfait", "excellent", "genial") and len(text) < 30:
        return "Avec plaisir ! N'hésitez pas si vous avez d'autres questions."

    if _any(text, "aide", "help", "que sais tu faire", "fonction", "capacite"):
        return ("Je peux répondre sur :\n"
                "- Statistiques du parc (combien, en panne, en service)\n"
                "- Échéances (assurance, vignette, CT, permis, CNI)\n"
                "- Budget et coûts de maintenance\n"
                "- Véhicule spécifique (par immatriculation ou marque)\n"
                "- Vidanges et maintenance prédictive\n"
                "- Directions et affectations\n"
                "- Conducteurs et documents\n"
                "- Et toute autre question via l'IA avancée.")

    if _any(text, "combien de vehicule", "nombre de vehicule", "taille du parc", "combien de voiture", "total vehicule"):
        return (f"Le parc compte {p['total']} véhicule(s) : {p['en_service']} en service, "
                f"{p['en_maintenance']} en maintenance et {p['en_panne']} en panne. "
                f"{p['drivers']} conducteur(s) enregistré(s).")

    if _any(text, "conducteur", "chauffeur", "combien de conducteur", "nombre de conducteur"):
        return f"Le parc compte {p['drivers']} conducteur(s) enregistré(s)."

    if _any(text, "en panne", "vehicules en panne", "voiture en panne", "pannes"):
        if p["en_panne"] == 0:
            return "Aucun véhicule n'est actuellement déclaré en panne."
        return f"{p['en_panne']} véhicule(s) sont actuellement en panne."

    if _any(text, "en maintenance", "maintenance en cours"):
        return f"{p['en_maintenance']} véhicule(s) sont actuellement en maintenance."

    if _any(text, "permis") and _any(text, "expir", "renouv", "valid", "echeance", "bientot"):
        driver_alerts = [a for a in (ctx["alertes_urgentes"] + ctx["alertes_a_venir"]) if a.get("type") == "permis"]
        if not driver_alerts:
            return "Aucun permis de conduire n'arrive à échéance prochainement."
        top = "\n".join(f"- {a.get('vehicle','')} : {a['msg']}" for a in driver_alerts[:8])
        return f"{len(driver_alerts)} permis à surveiller :\n{top}"

    if _any(text, "cni", "carte identite", "identite nationale", "carte nationale"):
        cni_alerts = [a for a in (ctx["alertes_urgentes"] + ctx["alertes_a_venir"]) if a.get("type") == "cni"]
        if not cni_alerts:
            return "Aucune CNI n'arrive à échéance prochainement."
        top = "\n".join(f"- {a.get('vehicle','')} : {a['msg']}" for a in cni_alerts[:8])
        return f"{len(cni_alerts)} CNI à surveiller :\n{top}"

    if _any(text, "echeance", "expire", "expirent", "renouveler", "renouvellement", "a jour", "pas a jour"):
        urg = ctx["alertes_urgentes"]
        av = ctx["alertes_a_venir"]
        if not urg and not av:
            return "Toutes les échéances sont à jour : assurances, vignettes, contrôles techniques."
        parts = []
        if urg:
            top = "\n".join(f"- {a.get('vehicle','')} ({a.get('immatriculation','')}) — {a['msg']}" for a in urg[:8])
            parts.append(f"DÉPASSÉES ({len(urg)}) :\n{top}")
        if av:
            top = "\n".join(f"- {a.get('vehicle','')} ({a.get('immatriculation','')}) — {a['msg']}" for a in av[:8])
            parts.append(f"À VENIR sous 30j ({len(av)}) :\n{top}")
        return "\n\n".join(parts)

    if _any(text, "assurance") and _any(text, "expir", "echeance", "bientot", "valid"):
        ass_alerts = [a for a in (ctx["alertes_urgentes"] + ctx["alertes_a_venir"])
                      if "assurance" in (a.get("msg") or "").lower() or "assurance" in (a.get("type") or "").lower()]
        if not ass_alerts:
            return "Toutes les assurances sont à jour."
        top = "\n".join(f"- {a.get('vehicle','')} ({a.get('immatriculation','')}) : {a['msg']}" for a in ass_alerts[:8])
        return f"{len(ass_alerts)} assurance(s) à renouveler :\n{top}"

    if _any(text, "controle technique", "ct") and _any(text, "expir", "echeance", "bientot", "valid"):
        ct_alerts = [a for a in (ctx["alertes_urgentes"] + ctx["alertes_a_venir"])
                     if "controle" in (a.get("msg") or "").lower() or "ct" in (a.get("msg") or "").lower()]
        if not ct_alerts:
            return "Tous les contrôles techniques sont à jour."
        top = "\n".join(f"- {a.get('vehicle','')} ({a.get('immatriculation','')}) : {a['msg']}" for a in ct_alerts[:8])
        return f"{len(ct_alerts)} contrôle(s) technique à renouveler :\n{top}"

    if _any(text, "vignette") and _any(text, "expir", "echeance", "bientot"):
        vig_alerts = [a for a in (ctx["alertes_urgentes"] + ctx["alertes_a_venir"])
                      if "vignette" in (a.get("msg") or "").lower()]
        if not vig_alerts:
            return "Toutes les vignettes sont à jour."
        top = "\n".join(f"- {a.get('vehicle','')} ({a.get('immatriculation','')}) : {a['msg']}" for a in vig_alerts[:8])
        return f"{len(vig_alerts)} vignette(s) à renouveler :\n{top}"

    if _any(text, "carte grise", "carte-grise", "cgrise"):
        cg_alerts = [a for a in (ctx["alertes_urgentes"] + ctx["alertes_a_venir"])
                     if "carte grise" in (a.get("msg") or "").lower()]
        if _any(text, "expir", "echeance", "bientot"):
            if not cg_alerts:
                return "Toutes les cartes grises sont à jour."
            top = "\n".join(f"- {a.get('vehicle','')} ({a.get('immatriculation','')}) : {a['msg']}" for a in cg_alerts[:8])
            return f"{len(cg_alerts)} carte(s) grise(s) à renouveler :\n{top}"
        vehs_cg = [dict(r) for r in db.execute(
            "SELECT immatriculation, marque, modele, carte_grise, carte_grise_exp FROM vehicles WHERE carte_grise IS NOT NULL AND carte_grise != ''").fetchall()]
        if vehs_cg:
            lines = "\n".join(f"- {v['immatriculation']} {v['marque']} {v['modele']} : CG {v['carte_grise']} (exp: {v['carte_grise_exp'] or '—'})"
                               for v in vehs_cg[:15])
            return f"{len(vehs_cg)} véhicule(s) avec carte grise :\n{lines}"
        return "Aucune carte grise n'est enregistrée pour l'instant."

    if _any(text, "budget") and _any(text, "depass", "alerte", "ou en est", "situation", "etat", "resume"):
        if not ctx["budget_categories_en_alerte"]:
            if ctx["budget_total_prevu_fcfa"] == 0:
                return "Aucun plan budgétaire n'est encore importé pour cette année."
            return (f"Budget {ctx['budget_annee']} maîtrisé : "
                    f"{_fmt_fcfa(ctx['budget_total_realise_fcfa'])} / {_fmt_fcfa(ctx['budget_total_prevu_fcfa'])} prévus. "
                    f"Aucune catégorie en alerte.")
        cats = "\n".join(f"- {b['categorie']} : {b['taux']}% consommé" for b in ctx["budget_categories_en_alerte"][:6])
        return (f"Budget {ctx['budget_annee']} : {_fmt_fcfa(ctx['budget_total_realise_fcfa'])} / "
                f"{_fmt_fcfa(ctx['budget_total_prevu_fcfa'])} prévus.\nCatégories en alerte :\n{cats}")

    if _any(text, "combien coute", "cout total", "depense totale", "combien a coute", "montant total"):
        return (f"Réalisé {ctx['budget_annee']} : {_fmt_fcfa(ctx['budget_total_realise_fcfa'])} "
                f"(prévu : {_fmt_fcfa(ctx['budget_total_prevu_fcfa'])}).")

    if _any(text, "plus cher", "plus couteux", "coute le plus", "top depense", "vehicule le plus"):
        top = ctx["vehicules_plus_couteux"]
        if not top or not top[0]["total"]:
            return "Aucune dépense de maintenance enregistrée pour l'instant."
        lines = "\n".join(f"{i+1}. {v['marque']} {v['modele']} ({v['immatriculation']}) — {_fmt_fcfa(v['total'])}"
                           for i, v in enumerate(top[:5]))
        return f"Top 5 des véhicules les plus coûteux :\n{lines}"

    if _any(text, "prochaine vidange", "vidange a prevoir", "vidange bientot", "vidange prochaine"):
        vidanges = [f for f in ctx["maintenance_predictive_proche"] if _norm(f.get("type", "")) == "vidange"]
        if not vidanges:
            return "Aucune vidange urgente à prévoir."
        v = vidanges[0]
        return f"Prochaine vidange : {v['marque']} {v['modele']} ({v['immatriculation']}), prévue vers le {v['date_due']}."

    if _any(text, "maintenance predictive", "prevision maintenance", "prochaines interventions", "a prevoir"):
        items = ctx["maintenance_predictive_proche"]
        if not items:
            return "Aucune intervention de maintenance prédite à court terme."
        top = "\n".join(f"- {f['marque']} {f['modele']} ({f['immatriculation']}) — {f['type']} vers le {f['date_due']}"
                         for f in items[:8])
        return f"{len(items)} intervention(s) prédite(s) :\n{top}"

    if _any(text, "direction"):
        ent = _extract_entities(text)
        d_name = ent.get("direction", "")
        if d_name:
            vehs = db_execute_list(ctx, f"SELECT immatriculation, marque, modele, statut, affectation FROM vehicles WHERE direction LIKE '%{d_name}%'")
            if vehs:
                lines = "\n".join(f"- {v['immatriculation']} {v['marque']} {v['modele']} ({v['statut']}) {v.get('affectation', '') or ''}"
                                   for v in vehs[:15])
                return f"{len(vehs)} véhicule(s) dans « {d_name.title()} » :\n{lines}"
            return f"Aucun véhicule trouvé pour la direction « {d_name.title()} »."
        all_dirs = db_execute_list(ctx, "SELECT direction, COUNT(*) as n FROM vehicles WHERE direction IS NOT NULL AND direction != '' GROUP BY direction ORDER BY n DESC")
        if all_dirs:
            lines = "\n".join(f"- {d['direction']}: {d['n']} véhicule(s)" for d in all_dirs)
            return f"Directions enregistrées :\n{lines}"
        return "Aucune direction n'est encore enregistrée. Ajoutez une direction dans la fiche de chaque véhicule."

    if _any(text, "marque"):
        ent = _extract_entities(text)
        marque = ent.get("marque", "")
        if marque:
            vehs = db_execute_list(ctx, f"SELECT immatriculation, modele, annee, statut FROM vehicles WHERE marque LIKE '%{marque}%'")
            if vehs:
                lines = "\n".join(f"- {v['immatriculation']} {v['modele']} ({v.get('annee', '?')}) — {v['statut']}" for v in vehs[:15])
                return f"{len(vehs)} véhicule(s) {marque.title()} :\n{lines}"
            return f"Aucun véhicule de marque {marque.title()} trouvé."
        return None

    return None


def db_execute_list(ctx, sql):
    """Helper pour exécuter du SQL dans les règles."""
    try:
        from db import get_db
        db = get_db()
        rows = [dict(r) for r in db.execute(sql).fetchall()]
        db.close()
        return rows
    except Exception:
        return []


# ---------------------------------------------------------------- appel OpenRouter (optionnel)
def _api_key():
    return os.environ.get("OPENROUTER_API_KEY") or (get_setting("openrouter_api_key", "") or "").strip()


def _model():
    return get_setting("assistant_model", DEFAULT_MODEL) or DEFAULT_MODEL


def ai_available():
    return bool(_api_key())


def _build_system_prompt(ctx):
    """Construit un system prompt enrichi avec les listes d'entités."""
    base = (
        "Tu es l'assistant intelligent de NexFleet, une application de gestion de parc automobile au Cameroun. "
        "Réponds en français, de façon concise (3-5 phrases max), professionnelle et directement exploitable. "
        "Base-toi UNIQUEMENT sur les données JSON fournies dans le contexte : n'invente jamais de chiffre, "
        "de véhicule ou d'échéance qui n'y figure pas. Si l'information demandée n'est pas présente dans "
        "le contexte, dis-le clairement et propose où la trouver dans l'application. "
        "Utilise des emojis avec modération. Le budget est en FCFA."
    )
    vehs = ctx.get("liste_vehicules", [])
    if vehs:
        veh_list = ", ".join(f"{v['immatriculation']} ({v['marque']} {v['modele']}, {v.get('direction', 'N/A')})"
                              for v in vehs[:40])
        base += f"\n\nVéhicules du parc ({len(vehs)} total) : {veh_list}"
    return base


def _call_openrouter(question, ctx, history):
    """Appel OpenRouter avec mémoire conversationnelle."""
    key = _api_key()
    if not key:
        return None

    system = _build_system_prompt(ctx)
    messages = [{"role": "system", "content": system}]

    for h in history[-20:]:
        role = "assistant" if h["role"] == "bot" else "user"
        messages.append({"role": role, "content": h["content"]})

    user_msg = f"Contexte JSON du parc :\n{json.dumps(ctx, ensure_ascii=False, default=str)}\n\nQuestion : {question}"
    messages.append({"role": "user", "content": user_msg})

    body = {
        "model": _model(),
        "max_tokens": 600,
        "temperature": 0.3,
        "messages": messages,
    }
    req = urllib.request.Request(
        OPENROUTER_API_URL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://nexfleet.local",
            "X-Title": "NexFleet Assistant",
        })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        choices = data.get("choices", [])
        if not choices:
            return None
        msg = choices[0].get("message", {})
        text = msg.get("content") or msg.get("reasoning_content") or ""
        if not text:
            return None
        return text.strip()
    except Exception:
        return None


# ---------------------------------------------------------------- point d'entrée
def answer(db, question, user_id=None):
    """Point d'entrée principal. Retourne {"answer": str, "source": str}."""
    question = (question or "").strip()
    if not question:
        return {"answer": "Posez-moi une question sur votre parc — échéances, budget, coûts, maintenance…",
                "source": "local"}

    history = _get_history(db, user_id)
    _save_history(db, user_id, "user", question)

    entities = _extract_entities(question)
    ctx = _rag_context(db, question, entities)
    text = _norm(question)

    local = _rule_answers(text, ctx)
    if local:
        _save_history(db, user_id, "assistant", local)
        return {"answer": local, "source": "local"}

    if ai_available():
        ai = _call_openrouter(question, ctx, history)
        if ai:
            _save_history(db, user_id, "assistant", ai)
            return {"answer": ai, "source": "openrouter"}

    hint = ("Je n'ai pas de réponse directe pour cette question. Essayez par exemple : "
            "« quelles échéances arrivent bientôt ? », « où en est le budget ? », "
            "« quel véhicule coûte le plus cher ? » ou « quelle est la prochaine vidange ? ».")
    if not ai_available():
        hint += (" Pour des réponses en langage libre, un administrateur peut "
                 "activer l'assistant IA dans Paramètres.")
    return {"answer": hint, "source": "local"}
