# -*- coding: utf-8 -*-
"""Tests d'authentification : inscription, connexion, profil, mot de passe."""
import pytest

from conftest import auth, register


def test_register_first_user_is_admin(client):
    r = register(client, "admin", "admin@test.fr", "Admin1234")
    assert r.status_code == 201
    body = r.get_json()
    assert body["token"]
    assert body["user"]["role"] == "admin"


def test_register_second_user_is_user(client):
    register(client, "admin", "admin@test.fr", "Admin1234")
    r = register(client, "user", "user@test.fr", "User1234")
    assert r.status_code == 201
    assert r.get_json()["user"]["role"] == "user"


@pytest.mark.parametrize("payload", [
    {"username": "ab", "email": "ok@test.fr", "password": "Abcdef12"},          # username trop court
    {"username": "okuser", "email": "pas-un-email", "password": "Abcdef12"},    # email invalide
    {"username": "okuser", "email": "ok@test.fr", "password": "court"},         # mdp trop court
    {"username": "okuser", "email": "ok@test.fr", "password": "abcdefgh"},      # mdp sans chiffre
])
def test_register_validation_errors(client, payload):
    r = register(client, **payload)
    assert r.status_code == 400


def test_register_duplicate(client):
    register(client, "admin", "admin@test.fr", "Admin1234")
    r = register(client, "admin2", "admin@test.fr", "Admin1234")
    assert r.status_code == 409


def test_login_success(client):
    register(client, "admin", "admin@test.fr", "Admin1234")
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin1234"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["token"]
    assert body["user"]["username"] == "admin"


def test_login_by_email(client):
    register(client, "admin", "admin@test.fr", "Admin1234")
    r = client.post("/api/auth/login", json={"email": "ADMIN@test.fr", "password": "Admin1234"})
    assert r.status_code == 200


def test_login_wrong_password(client):
    register(client, "admin", "admin@test.fr", "Admin1234")
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Mauvais123"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/auth/login", json={"username": "nobody", "password": "Nobody123"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth("token.invalide")).status_code == 401


def test_me_returns_profile(client, admin):
    r = client.get("/api/auth/me", headers=auth(admin))
    assert r.status_code == 200
    user = r.get_json()["user"]
    assert user["username"] == "admin"
    assert user["role"] == "admin"


def test_change_password(client, admin):
    r = client.put("/api/auth/password", headers=auth(admin),
                   json={"old_password": "Admin1234", "new_password": "Nouveau1234"})
    assert r.status_code == 200
    # l'ancien mot de passe ne fonctionne plus
    assert client.post("/api/auth/login",
                       json={"username": "admin", "password": "Admin1234"}).status_code == 401
    assert client.post("/api/auth/login",
                       json={"username": "admin", "password": "Nouveau1234"}).status_code == 200


def test_change_password_wrong_old(client, admin):
    r = client.put("/api/auth/password", headers=auth(admin),
                   json={"old_password": "Erreur123", "new_password": "Nouveau1234"})
    assert r.status_code == 401


def test_admin_required_is_enforced(client, user):
    r = client.get("/api/users", headers=auth(user))
    assert r.status_code == 403
