# -*- coding: utf-8 -*-
"""Fixtures de test — base SQLite isolée dans un dossier temporaire.

Le chemin de la base est redirigé vers un dossier temporaire AVANT
l'import d'``app`` (qui appelle ``init_db()`` à l'import).
"""
import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="necfleet_tests_")

import db  # noqa: E402

db.DATA_DIR = _TMP
db.UPLOAD_DIR = os.path.join(_TMP, "uploads")
db.DB_PATH = os.path.join(_TMP, "parc.db")

from app import app as flask_app  # noqa: E402

TABLES = [
    "users", "vehicles", "settings", "odometer", "documents",
    "tires", "drivers", "controls", "maintenance", "audit_log",
    "vidanges",
]


def reset_db():
    conn = db.get_db()
    for t in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()
    conn.close()
    db.init_db()


@pytest.fixture()
def app():
    reset_db()
    return flask_app


@pytest.fixture()
def client(app):
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, username, email, password):
    return client.post("/api/auth/register",
                       json={"username": username, "email": email, "password": password})


@pytest.fixture()
def admin(client):
    r = register(client, "admin", "admin@test.fr", "Admin1234")
    return r.get_json()["token"]


@pytest.fixture()
def user(client):
    register(client, "admin", "admin@test.fr", "Admin1234")
    r = register(client, "user", "user@test.fr", "User1234")
    return r.get_json()["token"]


def make_vehicle(client, token, **over):
    data = {
        "immatriculation": "AB-123-CD",
        "marque": "Renault",
        "modele": "Master",
        "annee": 2021,
        "type": "Utilitaire",
        "carburant": "Diesel",
        "kilometrage": 25000,
        "statut": "En service",
    }
    data.update(over)
    return client.post("/api/vehicles", json=data, headers=auth(token))


@pytest.fixture()
def vehicle(client, admin):
    r = make_vehicle(client, admin)
    assert r.status_code == 201
    return r.get_json()["id"]
