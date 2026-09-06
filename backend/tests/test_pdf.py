# -*- coding: utf-8 -*-
"""Tests des rapports PDF (parc, mensuel, fiche véhicule)."""
from conftest import auth, make_vehicle

PDF_MAGIC = b"%PDF"


def _assert_pdf(resp):
    assert resp.status_code == 200
    assert "application/pdf" in resp.content_type
    assert resp.data.startswith(PDF_MAGIC)


def test_parc_pdf(client, admin):
    make_vehicle(client, admin, immatriculation="AB-111-AA", marque="Renault", modele="Master")
    _assert_pdf(client.get("/api/parc/pdf", headers=auth(admin)))


def test_parc_pdf_requires_auth(client):
    assert client.get("/api/parc/pdf").status_code == 401


def test_monthly_report_pdf(client, admin):
    vid = make_vehicle(client, admin).get_json()["id"]
    client.post("/api/maintenance", headers=auth(admin), json={
        "vehicle_id": vid, "type": "Révision", "cout": 120})
    client.post("/api/controls", headers=auth(admin), json={"vehicle_id": vid})
    _assert_pdf(client.get("/api/reports/monthly/pdf", headers=auth(admin)))


def test_vehicle_pdf(client, admin, vehicle):
    _assert_pdf(client.get(f"/api/vehicles/{vehicle}/pdf", headers=auth(admin)))


def test_vehicle_pdf_404(client, admin):
    assert client.get("/api/vehicles/99999/pdf", headers=auth(admin)).status_code == 404
