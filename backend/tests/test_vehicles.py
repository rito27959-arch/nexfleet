# -*- coding: utf-8 -*-
"""Tests des véhicules : CRUD, recherche, détail, photos (vignette), documents, relevés."""
import io
import os

import pytest
from PIL import Image

from conftest import auth, make_vehicle


def tiny_image_bytes(fmt="JPEG"):
    buf = io.BytesIO()
    Image.new("RGB", (640, 480), (200, 40, 40)).save(buf, fmt)
    return buf.getvalue()


@pytest.fixture()
def vid(client, admin):
    r = make_vehicle(client, admin)
    assert r.status_code == 201
    return r.get_json()["id"]


def test_create_vehicle(client, admin):
    r = make_vehicle(client, admin)
    assert r.status_code == 201
    assert r.get_json()["id"] > 0


def test_create_vehicle_requires_auth(client):
    assert make_vehicle(client, "fake").status_code == 401


def test_create_vehicle_duplicate_immat(client, admin):
    make_vehicle(client, admin)
    r = make_vehicle(client, admin, marque="Peugeot", modele="Expert")
    assert r.status_code == 409


@pytest.mark.parametrize("over", [
    {"immatriculation": "AB"},
    {"marque": "", "modele": "Master"},
    {"annee": 1800},
    {"assurance_exp": "01/01/2025"},
])
def test_create_vehicle_validation(client, admin, over):
    r = make_vehicle(client, admin, **over)
    assert r.status_code == 400


def test_list_vehicles(client, admin, vid):
    r = client.get("/api/vehicles", headers=auth(admin))
    assert r.status_code == 200
    vehicles = r.get_json()["vehicles"]
    assert len(vehicles) == 1
    assert vehicles[0]["id"] == vid
    assert "alerts" in vehicles[0]
    assert vehicles[0]["photo_thumb"] is None


def test_list_vehicles_search_and_filters(client, admin):
    make_vehicle(client, admin, immatriculation="AB-111-AA", marque="Renault", statut="En service")
    make_vehicle(client, admin, immatriculation="CD-222-BB", marque="Peugeot", statut="En panne")
    h = auth(admin)
    assert len(client.get("/api/vehicles?search=peugeot", headers=h).get_json()["vehicles"]) == 1
    assert len(client.get("/api/vehicles?statut=panne", headers=h).get_json()["vehicles"]) == 1
    assert len(client.get("/api/vehicles?carburant=Essence", headers=h).get_json()["vehicles"]) == 0


def test_vehicle_detail(client, admin, vid):
    r = client.get(f"/api/vehicles/{vid}/detail", headers=auth(admin))
    assert r.status_code == 200
    body = r.get_json()
    assert body["vehicle"]["immatriculation"] == "AB-123-CD"
    assert body["controls"] == []
    assert body["maintenance"] == []


def test_vehicle_detail_404(client, admin):
    assert client.get("/api/vehicles/99999/detail", headers=auth(admin)).status_code == 404


def test_update_vehicle(client, admin, vid):
    r = client.put(f"/api/vehicles/{vid}", headers=auth(admin),
                   json={"immatriculation": "AB-123-CD", "marque": "Renault",
                         "modele": "Trafic", "kilometrage": 31000})
    assert r.status_code == 200
    detail = client.get(f"/api/vehicles/{vid}/detail", headers=auth(admin)).get_json()
    assert detail["vehicle"]["modele"] == "Trafic"
    assert detail["vehicle"]["kilometrage"] == 31000


def test_delete_vehicle(client, admin, user, vid):
    assert client.delete(f"/api/vehicles/{vid}", headers=auth(user)).status_code == 403
    r = client.delete(f"/api/vehicles/{vid}", headers=auth(admin))
    assert r.status_code == 200
    assert client.get("/api/vehicles", headers=auth(admin)).get_json()["vehicles"] == []


def test_upload_photo_generates_thumb(client, admin, vid):
    raw = tiny_image_bytes()
    data = {"photo": (io.BytesIO(raw), "photo.jpg")}
    r = client.post(f"/api/vehicles/{vid}/photo", headers=auth(admin), data=data,
                    content_type="multipart/form-data")
    assert r.status_code == 200
    body = r.get_json()
    assert body["photo"].startswith("/uploads/")
    assert body["photo_thumb"].startswith("/uploads/")
    assert body["photo_thumb"].endswith("_thumb.jpg")
    # le thumbnail est réellement plus petit que l'original et servi en HTTP 200
    t = client.get(body["photo_thumb"])
    assert t.status_code == 200
    assert len(t.data) < len(raw)
    # le véhicule expose bien la vignette
    v = client.get("/api/vehicles", headers=auth(admin)).get_json()["vehicles"][0]
    assert v["photo_thumb"] == body["photo_thumb"]


def test_upload_photo_invalid_file(client, admin, vid):
    data = {"photo": (io.BytesIO(b"pas une image"), "fichier.jpg")}
    r = client.post(f"/api/vehicles/{vid}/photo", headers=auth(admin), data=data,
                    content_type="multipart/form-data")
    assert r.status_code == 400


def test_upload_photo_missing_file(client, admin, vid):
    r = client.post(f"/api/vehicles/{vid}/photo", headers=auth(admin),
                    data={}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_delete_photo(client, admin, vid):
    data = {"photo": (io.BytesIO(tiny_image_bytes()), "photo.jpg")}
    client.post(f"/api/vehicles/{vid}/photo", headers=auth(admin), data=data,
                content_type="multipart/form-data")
    r = client.delete(f"/api/vehicles/{vid}/photo", headers=auth(admin))
    assert r.status_code == 200
    v = client.get("/api/vehicles", headers=auth(admin)).get_json()["vehicles"][0]
    assert v["photo"] is None
    assert v["photo_thumb"] is None


def test_upload_document_and_delete(client, admin, vid):
    data = {"file": (io.BytesIO(b"contenu du pdf"), "carte_grise.pdf"), "label": "Carte grise"}
    r = client.post(f"/api/vehicles/{vid}/documents", headers=auth(admin), data=data,
                    content_type="multipart/form-data")
    assert r.status_code == 201
    did = r.get_json()["id"]
    docs = client.get(f"/api/vehicles/{vid}/documents", headers=auth(admin)).get_json()["documents"]
    assert any(d["id"] == did for d in docs)
    assert client.delete(f"/api/documents/{did}", headers=auth(admin)).status_code == 200


def test_odometer_crud(client, admin, vid):
    h = auth(admin)
    r = client.post(f"/api/vehicles/{vid}/odometer", headers=h,
                    json={"kilometres": 25100, "date": "2026-01-15", "note": "Plein"})
    assert r.status_code == 201
    oid = r.get_json()["id"]
    rows = client.get(f"/api/vehicles/{vid}/odometer", headers=h).get_json()["odometer"]
    assert any(x["id"] == oid and x["kilometres"] == 25100 for x in rows)
    assert client.delete(f"/api/odometer/{oid}", headers=h).status_code == 200


def test_odometer_invalid_km(client, admin, vid):
    r = client.post(f"/api/vehicles/{vid}/odometer", headers=auth(admin),
                    json={"kilometres": "abc"})
    assert r.status_code == 400


def test_photo_thumb_db_migration_present(client, admin, vid):
    """La colonne photo_thumb doit exister et être retournée par l'API."""
    v = client.get(f"/api/vehicles/{vid}/detail", headers=auth(admin)).get_json()["vehicle"]
    assert "photo_thumb" in v
