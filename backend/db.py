# -*- coding: utf-8 -*-
"""Couche d'accès aux données — SQLite (stdlib, zéro dépendance)."""

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
# Répertoires surchargeables (déploiement cloud / disque persistant).
DATA_DIR = os.environ.get("NEXFLEET_DATA_DIR") or os.path.join(PROJECT_DIR, "data")
UPLOAD_DIR = os.environ.get("NEXFLEET_UPLOAD_DIR") or os.path.join(PROJECT_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "parc.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vehicles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    immatriculation TEXT UNIQUE NOT NULL,
    marque          TEXT NOT NULL,
    modele          TEXT NOT NULL,
    annee           INTEGER,
    type            TEXT DEFAULT 'Utilitaire',
    carburant       TEXT DEFAULT 'Diesel',
    kilometrage     INTEGER DEFAULT 0,
    vignette_exp    TEXT,
    assurance_exp   TEXT,
    ctrl_tech_exp   TEXT,
    vignette_note   TEXT,
    ct_note         TEXT,
    carte_grise_note TEXT,
    statut          TEXT DEFAULT 'En service',
    direction       TEXT,
    affectation     TEXT,
    photo           TEXT,
    photo_thumb     TEXT,
    num_chassis     TEXT,
    num_moteur      TEXT,
    carte_grise      TEXT,
    carte_grise_exp  TEXT,
    cv              INTEGER,
    lat             REAL,
    lng             REAL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS odometer (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    date       TEXT NOT NULL,
    kilometres INTEGER NOT NULL,
    note       TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    label      TEXT,
    filename   TEXT NOT NULL,
    stored     TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tires (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id         INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    position           TEXT NOT NULL,
    marque             TEXT,
    taille             TEXT,
    etat               TEXT DEFAULT 'Bon',
    date_montage       TEXT,
    date_remplacement  TEXT,
    note               TEXT,
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drivers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nom        TEXT NOT NULL,
    prenom     TEXT NOT NULL,
    matricule  TEXT,
    email      TEXT,
    telephone  TEXT,
    permis     TEXT,
    permis_exp TEXT,
    cni        TEXT,
    cni_exp    TEXT,
    permis_note TEXT,
    cni_note    TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS controls (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    driver_id  INTEGER REFERENCES drivers(id) ON DELETE SET NULL,
    date       TEXT NOT NULL,
    type       TEXT NOT NULL,
    resultat   TEXT NOT NULL,
    notes      TEXT,
    items      TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS maintenance (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    type       TEXT NOT NULL,
    date       TEXT NOT NULL,
    cout       REAL DEFAULT 0,
    garage     TEXT,
    notes      TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vidanges (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id            INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    date                  TEXT NOT NULL,
    km                    INTEGER DEFAULT 0,
    huile                 TEXT,
    quantite              REAL DEFAULT 0,
    filtre                INTEGER DEFAULT 0,
    filtre_huile          INTEGER DEFAULT 0,
    filtre_gasoil         INTEGER DEFAULT 0,
    huile_transmission    INTEGER DEFAULT 0,
    liquide_refroidissement INTEGER DEFAULT 0,
    liquide_laveglace     INTEGER DEFAULT 0,
    km_interval           INTEGER DEFAULT 0,
    cout                  REAL DEFAULT 0,
    garage                TEXT,
    notes                 TEXT,
    prochaine_km          INTEGER DEFAULT 0,
    created_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budget_plan (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    annee                INTEGER NOT NULL,
    domaine              TEXT NOT NULL DEFAULT 'parc_auto',
    service               TEXT,
    activite             TEXT,
    categorie            TEXT,
    categorie_std        TEXT NOT NULL DEFAULT 'Autre',
    tache                TEXT NOT NULL,
    q1_qte               REAL DEFAULT 0,
    q1_montant           REAL DEFAULT 0,
    q2_qte               REAL DEFAULT 0,
    q2_montant           REAL DEFAULT 0,
    q3_qte               REAL DEFAULT 0,
    q3_montant           REAL DEFAULT 0,
    q4_qte               REAL DEFAULT 0,
    q4_montant           REAL DEFAULT 0,
    qte_annuelle         REAL DEFAULT 0,
    prix_unitaire        REAL DEFAULT 0,
    montant_annuel       REAL DEFAULT 0,
    mois_concerne        TEXT,
    regle_mensualisation TEXT,
    source_fichier       TEXT,
    created_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    username   TEXT,
    action     TEXT NOT NULL,
    entity     TEXT,
    entity_id  INTEGER,
    details    TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_controls_vehicle ON controls(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle ON maintenance(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vidanges_vehicle ON vidanges(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_statut ON vehicles(statut);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_odometer_vehicle ON odometer(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_documents_vehicle ON documents(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_tires_vehicle ON tires(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_budget_annee ON budget_plan(annee);
CREATE INDEX IF NOT EXISTS idx_budget_categorie ON budget_plan(categorie_std);
CREATE INDEX IF NOT EXISTS idx_budget_domaine ON budget_plan(domaine);

CREATE TABLE IF NOT EXISTS chat_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id, created_at);
"""


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


MIGRATIONS = [
    ("vehicles", "affectation", "ALTER TABLE vehicles ADD COLUMN affectation TEXT"),
    ("vehicles", "photo", "ALTER TABLE vehicles ADD COLUMN photo TEXT"),
    ("vehicles", "photo_thumb", "ALTER TABLE vehicles ADD COLUMN photo_thumb TEXT"),
    ("drivers", "matricule", "ALTER TABLE drivers ADD COLUMN matricule TEXT"),
    ("drivers", "cni_exp", "ALTER TABLE drivers ADD COLUMN cni_exp TEXT"),
    ("vehicles", "num_chassis", "ALTER TABLE vehicles ADD COLUMN num_chassis TEXT"),
    ("vehicles", "num_moteur", "ALTER TABLE vehicles ADD COLUMN num_moteur TEXT"),
    ("vehicles", "cv", "ALTER TABLE vehicles ADD COLUMN cv INTEGER"),
    ("vehicles", "lat", "ALTER TABLE vehicles ADD COLUMN lat REAL"),
    ("vehicles", "lng", "ALTER TABLE vehicles ADD COLUMN lng REAL"),
    ("vehicles", "direction", "ALTER TABLE vehicles ADD COLUMN direction TEXT"),
("vehicles", "carte_grise", "ALTER TABLE vehicles ADD COLUMN carte_grise TEXT"),
("vehicles", "carte_grise_exp", "ALTER TABLE vehicles ADD COLUMN carte_grise_exp TEXT"),
("vehicles", "vignette_note", "ALTER TABLE vehicles ADD COLUMN vignette_note TEXT"),
("vehicles", "ct_note", "ALTER TABLE vehicles ADD COLUMN ct_note TEXT"),
("vehicles", "carte_grise_note", "ALTER TABLE vehicles ADD COLUMN carte_grise_note TEXT"),
("drivers", "cni", "ALTER TABLE drivers ADD COLUMN cni TEXT"),
("drivers", "permis_note", "ALTER TABLE drivers ADD COLUMN permis_note TEXT"),
("drivers", "cni_note", "ALTER TABLE drivers ADD COLUMN cni_note TEXT"),
("vidanges", "filtre_huile", "ALTER TABLE vidanges ADD COLUMN filtre_huile INTEGER DEFAULT 0"),
("vidanges", "filtre_gasoil", "ALTER TABLE vidanges ADD COLUMN filtre_gasoil INTEGER DEFAULT 0"),
("vidanges", "huile_transmission", "ALTER TABLE vidanges ADD COLUMN huile_transmission INTEGER DEFAULT 0"),
("vidanges", "liquide_refroidissement", "ALTER TABLE vidanges ADD COLUMN liquide_refroidissement INTEGER DEFAULT 0"),
("vidanges", "liquide_laveglace", "ALTER TABLE vidanges ADD COLUMN liquide_laveglace INTEGER DEFAULT 0"),
("vidanges", "km_interval", "ALTER TABLE vidanges ADD COLUMN km_interval INTEGER DEFAULT 0"),
]


def init_db():
    ensure_dirs()
    conn = get_db()
    conn.executescript(SCHEMA)
    for table, column, sql in MIGRATIONS:
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
        if column not in cols:
            conn.execute(sql)
    conn.execute("UPDATE vidanges SET filtre_huile = filtre WHERE filtre_huile = 0 AND filtre = 1")
    conn.commit()
    conn.close()


def now():
    return datetime.now().isoformat(timespec="seconds")


def get_setting(key, default=None, conn=None):
    if conn is not None:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row is not None else default
    c = get_db()
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return row["value"] if row is not None else default


def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
    conn.commit()
    conn.close()


def row_to_dict(row):
    return dict(row) if row is not None else None
