# -*- coding: utf-8 -*-
"""Tests maintenance, contrôles techniques, pneumatiques et conducteurs."""
import pytest

from conftest import auth, make_vehicle


@pytest.fixture()
def vid(client, admin):
    return make_vehicle(client, admin).get_json()["id"]


def test_maintenance_crud(client, admin, vid):
    h = auth(admin)
    r = client.post("/api/maintenance", headers=h, json={
        "vehicle_id": vid, "type": "Révision", "date": "2026-02-01",
        "cout": 240.5, "garage": "Garage Central", "notes": "Vidange + filtres"})
    assert r.status_code == 201
    mid = r.get_json()["id"]

    rows = client.get("/api/maintenance", headers=h).get_json()["maintenance"]
    row = next(x for x in rows if x["id"] == mid)
    assert row["immatriculation"] == "AB-123-CD"
    assert row["cout"] == 240.5

    r = client.put(f"/api/maintenance/{mid}", headers=h,
                   json={"vehicle_id": vid, "cout": 300, "notes": "màj"})
    assert r.status_code == 200
    rows = client.get("/api/maintenance", headers=h).get_json()["maintenance"]
    assert next(x for x in rows if x["id"] == mid)["cout"] == 300

    assert client.delete(f"/api/maintenance/{mid}", headers=h).status_code == 200
    assert client.delete(f"/api/maintenance/{mid}", headers=h).status_code == 404


def test_maintenance_unknown_vehicle(client, admin):
    r = client.post("/api/maintenance", headers=auth(admin), json={"vehicle_id": 9999})
    assert r.status_code == 404


def test_maintenance_forecast(client, admin, vid):
    client.post("/api/maintenance", headers=auth(admin), json={
        "vehicle_id": vid, "type": "Révision", "date": "2026-01-01"})
    r = client.get("/api/maintenance/forecast", headers=auth(admin))
    assert r.status_code == 200
    row = next(x for x in r.get_json()["forecast"] if x["vehicle_id"] == vid)
    assert row["immatriculation"] == "AB-123-CD"
    assert row["km_due"] > 0
    assert row["date_due"]


def test_controls_crud(client, admin, vid):
    h = auth(admin)
    r = client.post("/api/controls", headers=h, json={
        "vehicle_id": vid, "date": "2026-03-10", "type": "Contrôle technique",
        "resultat": "Conforme", "notes": "RAS"})
    assert r.status_code == 201
    cid = r.get_json()["id"]
    rows = client.get(f"/api/controls/vehicle/{vid}", headers=h).get_json()["controls"]
    assert any(x["id"] == cid for x in rows)
    assert client.put(f"/api/controls/{cid}", headers=h,
                      json={"vehicle_id": vid, "resultat": "Non conforme"}).status_code == 200
    assert client.delete(f"/api/controls/{cid}", headers=h).status_code == 200


def test_controls_list_global(client, admin, vid):
    client.post("/api/controls", headers=auth(admin), json={"vehicle_id": vid})
    r = client.get("/api/controls", headers=auth(admin))
    assert r.status_code == 200
    assert len(r.get_json()["controls"]) == 1


def test_tires_crud(client, admin, vid):
    h = auth(admin)
    r = client.post(f"/api/vehicles/{vid}/tires", headers=h, json={
        "position": "AVG", "marque": "Michelin", "taille": "205/65 R16",
        "etat": "Bon", "date_montage": "2025-06-01"})
    assert r.status_code == 201
    tid = r.get_json()["id"]
    rows = client.get(f"/api/vehicles/{vid}/tires", headers=h).get_json()["tires"]
    assert any(x["id"] == tid and x["position"] == "AVG" for x in rows)
    assert client.put(f"/api/tires/{tid}", headers=h,
                      json={"etat": "Usé"}).status_code == 200
    assert client.delete(f"/api/tires/{tid}", headers=h).status_code == 200


def test_drivers_crud(client, admin):
    h = auth(admin)
    r = client.post("/api/drivers", headers=h, json={
        "nom": "Durand", "prenom": "Jean", "matricule": "MAT-00123",
        "permis": "12345678901", "permis_exp": "2027-01-01"})
    assert r.status_code == 201
    did = r.get_json()["id"]
    rows = client.get("/api/drivers", headers=h).get_json()["drivers"]
    assert any(x["id"] == did and x["nom"] == "Durand" and x["matricule"] == "MAT-00123" for x in rows)
    assert client.put(f"/api/drivers/{did}", headers=h,
                      json={"nom": "Durand", "prenom": "Jean", "matricule": "MAT-00999",
                            "telephone": "0600000000"}).status_code == 200
    rows = client.get("/api/drivers", headers=h).get_json()["drivers"]
    assert next(x for x in rows if x["id"] == did)["matricule"] == "MAT-00999"
    assert client.delete(f"/api/drivers/{did}", headers=h).status_code == 200


def test_driver_requires_name(client, admin):
    r = client.post("/api/drivers", headers=auth(admin), json={"nom": "", "prenom": ""})
    assert r.status_code == 400
