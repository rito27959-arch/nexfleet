# -*- coding: utf-8 -*-
"""Tests tableau de bord : statistiques, calendrier, notifications, paramètres, sauvegarde, export."""
from conftest import auth, make_vehicle


def _seed(client, admin):
    make_vehicle(client, admin, immatriculation="AB-111-AA", marque="Renault", carburant="Diesel")
    make_vehicle(client, admin, immatriculation="CD-222-BB", marque="Peugeot", carburant="Essence")


def test_health_is_public(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_stats_requires_auth(client):
    assert client.get("/api/stats").status_code == 401


def test_stats_counts(client, admin):
    _seed(client, admin)
    r = client.get("/api/stats", headers=auth(admin))
    assert r.status_code == 200
    body = r.get_json()
    assert body["total"] == 2
    assert body["en_service"] == 2
    assert "carburant" in body and "marques" in body
    assert len(body["controls_by_month"]) == 6


def test_calendar_events(client, admin):
    make_vehicle(client, admin, assurance_exp="2026-12-31", vignette_exp="2027-05-01",
                 ctrl_tech_exp="2026-09-15")
    r = client.get("/api/calendar/events", headers=auth(admin))
    assert r.status_code == 200
    events = r.get_json()["events"]
    kinds = {e["type"] for e in events}
    assert {"assurance_exp", "vignette_exp", "ctrl_tech_exp"} <= kinds
    dates = [e["date"] for e in events]
    assert dates == sorted(dates)


def test_calendar_includes_driver_permis(client, admin):
    r = client.post("/api/drivers", headers=auth(admin), json={
        "nom": "Durand", "prenom": "Jean", "permis_exp": "2027-03-01"})
    assert r.status_code == 201
    events = client.get("/api/calendar/events", headers=auth(admin)).get_json()["events"]
    assert any(e["type"] == "permis" and e["kind"] == "driver" for e in events)


def test_calendar_includes_vidanges(client, admin):
    veh = make_vehicle(client, admin).get_json()["id"]
    client.post("/api/vidanges", headers=auth(admin), json={
        "vehicle_id": veh, "date": "2026-07-20", "km": 25000, "huile": "10W-40"})
    events = client.get("/api/calendar/events", headers=auth(admin)).get_json()["events"]
    vg = [e for e in events if e["type"] == "vidange"]
    assert len(vg) == 1
    assert vg[0]["date"] == "2026-07-20"
    assert vg[0]["label"] == "Vidange"
    assert vg[0]["kind"] == "vehicle"
    assert "km" in vg[0] and vg[0]["km"] == 25000


def test_notifications(client, admin):
    make_vehicle(client, admin, assurance_exp="2026-01-01", statut="En service")
    r = client.get("/api/notifications", headers=auth(admin))
    assert r.status_code == 200
    body = r.get_json()
    assert body["danger_count"] >= 1
    assert "events" in body


def test_settings_defaults(client, admin):
    r = client.get("/api/settings", headers=auth(admin))
    assert r.status_code == 200
    s = r.get_json()["settings"]
    assert s["alert_threshold"] == 30
    assert s["forecast_km"] == 10000
    assert s["vidange_alert_km"] == 500


def test_update_settings_admin_only(client, admin, user):
    r = client.put("/api/settings", headers=auth(user), json={"alert_threshold": 45})
    assert r.status_code == 403
    r = client.put("/api/settings", headers=auth(admin), json={
        "alert_threshold": 45, "forecast_km": 8000, "vidange_alert_km": 300})
    assert r.status_code == 200
    s = client.get("/api/settings", headers=auth(admin)).get_json()["settings"]
    assert s["alert_threshold"] == 45
    assert s["forecast_km"] == 8000
    assert s["vidange_alert_km"] == 300


def test_update_settings_invalid(client, admin):
    r = client.put("/api/settings", headers=auth(admin), json={"alert_threshold": "abc"})
    assert r.status_code == 400


def test_backup_requires_admin(client, admin, user):
    assert client.get("/api/backup", headers=auth(user)).status_code == 403
    r = client.get("/api/backup", headers=auth(admin))
    assert r.status_code == 200
    assert r.data[:16].startswith(b"SQLite format 3")


def test_demo_seeds_data(client, admin):
    r = client.post("/api/demo", headers=auth(admin))
    assert r.status_code == 200
    stats = client.get("/api/stats", headers=auth(admin)).get_json()
    assert stats["total"] > 0


def test_demo_rejected_when_data_exists(client, admin):
    make_vehicle(client, admin)
    r = client.post("/api/demo", headers=auth(admin))
    assert r.status_code == 409


def test_demo_admin_only(client, admin, user):
    assert client.post("/api/demo", headers=auth(user)).status_code == 403


def test_users_admin_crud(client, admin, user):
    h = auth(admin)
    users = client.get("/api/users", headers=h).get_json()["users"]
    assert len(users) == 2
    target = next(u for u in users if u["username"] == "user")
    r = client.put(f"/api/users/{target['id']}/role", headers=h, json={"role": "admin"})
    assert r.status_code == 200
    assert client.post("/api/users", headers=h, json={
        "username": "nouveau", "email": "nouveau@test.fr", "password": "Nouveau123", "role": "user"
    }).status_code == 201
    assert client.delete(f"/api/users/{target['id']}", headers=h).status_code == 200


def test_export_csv(client, admin):
    make_vehicle(client, admin)
    r = client.get("/api/export?format=csv", headers=auth(admin))
    assert r.status_code == 200
    assert "text/csv" in r.content_type
    assert len(r.data) > 0


def test_export_xlsx(client, admin):
    make_vehicle(client, admin)
    r = client.get("/api/export?format=xlsx", headers=auth(admin))
    assert r.status_code == 200
    assert r.data.startswith(b"PK")  # signature ZIP du .xlsx


def test_import_template(client, admin):
    r = client.get("/api/import/template", headers=auth(admin))
    assert r.status_code == 200


def test_audit_log_after_actions(client, admin):
    make_vehicle(client, admin)
    r = client.get("/api/audit", headers=auth(admin))
    assert r.status_code == 200
    assert "events" in r.get_json()
