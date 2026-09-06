# -*- coding: utf-8 -*-
"""Tests vidanges : CRUD, stats/prévisions et rapport PDF."""
import pytest

from conftest import auth, make_vehicle


@pytest.fixture()
def vid(client, admin):
    return make_vehicle(client, admin).get_json()["id"]


def test_vidange_crud(client, admin, vid):
    h = auth(admin)
    r = client.post("/api/vidanges", headers=h, json={
        "vehicle_id": vid, "date": "2026-03-01", "km": 40000, "huile": "10W-40",
        "quantite": 7, "filtre": True, "cout": 75.5, "garage": "Garage Central",
        "notes": "Vidange périodique"})
    assert r.status_code == 201
    gid = r.get_json()["id"]

    rows = client.get("/api/vidanges", headers=h).get_json()["vidanges"]
    row = next(x for x in rows if x["id"] == gid)
    assert row["immatriculation"] == "AB-123-CD"
    assert row["cout"] == 75.5
    assert row["prochaine_km"] >= 50000

    r = client.put(f"/api/vidanges/{gid}", headers=h,
                   json={"vehicle_id": vid, "km": 42000, "cout": 80, "filtre": False})
    assert r.status_code == 200
    rows = client.get("/api/vidanges", headers=h).get_json()["vidanges"]
    assert next(x for x in rows if x["id"] == gid)["cout"] == 80
    assert next(x for x in rows if x["id"] == gid)["filtre"] == 0

    assert client.delete(f"/api/vidanges/{gid}", headers=h).status_code == 200
    assert client.delete(f"/api/vidanges/{gid}", headers=h).status_code == 404


def test_vidange_unknown_vehicle(client, admin):
    r = client.post("/api/vidanges", headers=auth(admin), json={"vehicle_id": 9999})
    assert r.status_code == 404


def test_vidange_stats(client, admin, vid):
    h = auth(admin)
    client.post("/api/vidanges", headers=h, json={
        "vehicle_id": vid, "date": "2026-03-01", "km": 40000, "cout": 75.5})
    r = client.get("/api/vidanges/stats", headers=h)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1
    assert data["cost_total"] == 75.5
    assert data["this_year"] == 1
    assert data["by_vehicle"][0]["count"] == 1
    fc = next(x for x in data["forecast"] if x["vehicle_id"] == vid)
    assert fc["km_due"] >= 50000
    assert fc["immatriculation"] == "AB-123-CD"


def test_vidange_pdf(client, admin, vid):
    h = auth(admin)
    client.post("/api/vidanges", headers=h, json={
        "vehicle_id": vid, "date": "2026-03-01", "km": 40000, "cout": 75.5})
    r = client.get("/api/vidanges/pdf", headers=h)
    assert r.status_code == 200
    assert r.data[:4] == b"%PDF"
    assert client.get("/api/vidanges/pdf").status_code == 401


def test_vidange_pdf_empty(client, admin):
    r = client.get("/api/vidanges/pdf", headers=auth(admin))
    assert r.status_code == 200
    assert r.data[:4] == b"%PDF"


def test_vidange_history_and_detail(client, admin, vid):
    h = auth(admin)
    client.post("/api/vidanges", headers=h, json={
        "vehicle_id": vid, "date": "2026-03-01", "km": 40000, "cout": 75.5})
    r = client.get(f"/api/vehicles/{vid}/detail", headers=h)
    assert r.status_code == 200
    data = r.get_json()
    assert any(x["kind"] == "vidange" for x in data["history"])
    assert len(data["vidanges"]) == 1
    assert data["total_spent"] == 75.5


def test_stats_includes_vidanges(client, admin, vid):
    h = auth(admin)
    client.post("/api/vidanges", headers=h, json={
        "vehicle_id": vid, "date": "2026-03-01", "km": 40000, "cout": 100})
    r = client.get("/api/stats", headers=h)
    assert r.status_code == 200
    data = r.get_json()
    assert data["vidanges_count"] == 1
    assert data["vidanges_total"] == 100
    assert data["vidanges_year"] == 1


def test_vidange_km_alert(client, admin, vid):
    h = auth(admin)
    gid = client.post("/api/vidanges", headers=h, json={
        "vehicle_id": vid, "date": "2026-03-01", "km": 24000, "prochaine_km": 25400}).get_json()["id"]
    alerts = client.get("/api/notifications", headers=h).get_json()["alerts"]
    warn = [a for a in alerts if a["type"] == "vidange"]
    assert len(warn) == 1
    assert warn[0]["level"] == "warning"
    assert warn[0]["label"] == "Vidange"
    assert "dans 400 km" in warn[0]["msg"]

    detail = client.get(f"/api/vehicles/{vid}/detail", headers=h).get_json()
    assert any(a["type"] == "vidange" for a in detail["vehicle"]["alerts"])

    client.put(f"/api/vidanges/{gid}", headers=h,
               json={"vehicle_id": vid, "km": 24000, "prochaine_km": 24500})
    alerts = client.get("/api/notifications", headers=h).get_json()["alerts"]
    dang = [a for a in alerts if a["type"] == "vidange"]
    assert len(dang) == 1
    assert dang[0]["level"] == "danger"
    assert "dépassée de 500 km" in dang[0]["msg"]


def test_vidange_alert_threshold_configurable(client, admin, vid):
    h = auth(admin)
    client.put("/api/settings", headers=h, json={"vidange_alert_km": 200})
    gid = client.post("/api/vidanges", headers=h, json={
        "vehicle_id": vid, "date": "2026-03-01", "km": 24000, "prochaine_km": 25300}).get_json()["id"]
    alerts = client.get("/api/notifications", headers=h).get_json()["alerts"]
    assert not any(a["type"] == "vidange" for a in alerts)

    client.put(f"/api/vidanges/{gid}", headers=h,
               json={"vehicle_id": vid, "km": 24000, "prochaine_km": 25100})
    alerts = client.get("/api/notifications", headers=h).get_json()["alerts"]
    warn = [a for a in alerts if a["type"] == "vidange"]
    assert len(warn) == 1
    assert warn[0]["level"] == "warning"
    assert "dans 100 km" in warn[0]["msg"]
