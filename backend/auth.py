# -*- coding: utf-8 -*-
"""Authentification & autorisation — JWT (HS256), hachage des mots de passe."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secret")


def _load_secret():
    """Clé secrète persistante (générée une fois, jamais commitée).

    Priorité : variable d'environnement `SECRET_KEY` (déploiement
    cloud), puis fichier local `.secret`, puis génération aléatoire.
    """
    env_key = os.environ.get("SECRET_KEY", "").strip()
    if env_key:
        return env_key
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r", encoding="utf-8") as fh:
            key = fh.read().strip()
        if key:
            return key
    key = secrets.token_hex(48)
    try:
        with open(SECRET_FILE, "w", encoding="utf-8") as fh:
            fh.write(key)
    except OSError:
        pass
    return key


SECRET_KEY = _load_secret()


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256:150000", salt_length=16)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def create_token(user_id: int, role: str, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "name": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _decode(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"]), None
    except jwt.ExpiredSignatureError:
        return None, "Session expirée. Veuillez vous reconnecter."
    except jwt.InvalidTokenError:
        return None, "Token invalide ou corrompu."
    except Exception:
        return None, "Erreur d'authentification."


def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Authentification requise."}), 401
        payload, err = _decode(auth[7:].strip())
        if payload is None:
            return jsonify({"error": err}), 401
        request.user_id = int(payload["sub"])
        request.user_role = payload["role"]
        request.user_name = payload.get("name", "")
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if getattr(request, "user_role", None) != "admin":
            return jsonify({"error": "Action réservée aux administrateurs."}), 403
        return f(*args, **kwargs)
    return wrapper
