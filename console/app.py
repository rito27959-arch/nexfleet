# -*- coding: utf-8 -*-
"""NexFleet Console — gestion de la base de données et des connexions.
Console web façon Supabase/Firebase : explorateur de tables, SQL, utilisateurs, sauvegarde.
Port : 5001 (parallèle au serveur NexFleet sur 5000).
"""
import os
import re
import secrets
import shutil
import sqlite3
import sys
from datetime import datetime
from functools import wraps

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, session, url_for

CONSOLE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CONSOLE_DIR)
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
DATA_DIR = os.path.join(PROJECT_DIR, "data")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
CONSOLE_DB = os.path.join(DATA_DIR, "console.db")
SECRET_FILE = os.path.join(CONSOLE_DIR, ".console-secret")

sys.path.insert(0, BACKEND_DIR)
from db import DB_PATH, get_db, row_to_dict  # noqa: E402
from auth import hash_password, verify_password  # noqa: E402

app = Flask(__name__)


def _load_secret():
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r", encoding="utf-8") as fh:
            key = fh.read().strip()
        if key:
            return key
    key = secrets.token_hex(32)
    try:
        with open(SECRET_FILE, "w", encoding="utf-8") as fh:
            fh.write(key)
    except OSError:
        pass
    return key


app.secret_key = _load_secret()


def get_console_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(CONSOLE_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS console_users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at    TEXT NOT NULL)""")
    conn.commit()
    return conn


def console_user_count():
    conn = get_console_db()
    n = conn.execute("SELECT COUNT(*) AS n FROM console_users").fetchone()["n"]
    conn.close()
    return n


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("console_user"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Non connecté."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def table_names():
    conn = get_db()
    names = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    conn.close()
    return names


def is_table(name):
    return name in table_names()


def table_info(conn, table):
    valid = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if table not in valid:
        raise ValueError("Invalid table name")
    return [dict(r) for r in conn.execute(f"PRAGMA table_info({table})")]


# ------------------------------------------------------------------ pages
@app.get("/")
@login_required
def overview():
    conn = get_db()
    try:
        tables = []
        for t in table_names():
            tables.append({"name": t, "count": conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]})
        users_n = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        vehicles_n = conn.execute("SELECT COUNT(*) AS n FROM vehicles").fetchone()["n"]
        audit_n = conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]
    except Exception:
        users_n = vehicles_n = audit_n = 0
    finally:
        conn.close()
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    return render_template("overview.html", tables=tables, users_n=users_n, vehicles_n=vehicles_n,
                           audit_n=audit_n, db_size=db_size, db_path=DB_PATH)


@app.get("/tables")
@login_required
def tables_page():
    return render_template("tables.html", tables=table_names())


@app.get("/tables/<table>")
@login_required
def table_page(table):
    if not is_table(table):
        abort(404)
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(max(int(request.args.get("per_page", 50)), 5), 200)
    except (ValueError, TypeError):
        per_page = 50
    q = (request.args.get("q") or "").strip()
    conn = get_db()
    cols = table_info(conn, table)
    base = f"FROM {table} WHERE 1=1"
    params = []
    if q:
        text_cols = [c["name"] for c in cols if "INT" not in str(c["type"]).upper()]
        if text_cols:
            base += " AND (" + " OR ".join(f"{c} LIKE ?" for c in text_cols) + ")"
            params += [f"%{q}%"] * len(text_cols)
    total = conn.execute(f"SELECT COUNT(*) AS n {base}", params).fetchone()["n"]
    rows = [dict(r) for r in conn.execute(
        f"SELECT * {base} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page]).fetchall()]
    conn.close()
    pages = max((total + per_page - 1) // per_page, 1)
    return render_template("table.html", table=table, cols=cols, rows=rows, total=total,
                           page=page, pages=pages, per_page=per_page, q=q)


@app.get("/sql")
@login_required
def sql_page():
    return render_template("sql.html")


@app.get("/users")
@login_required
def users_page():
    conn = get_db()
    users = [dict(r) for r in conn.execute("SELECT * FROM users ORDER BY id").fetchall()]
    conn.close()
    return render_template("users.html", users=users)


@app.get("/connections")
@login_required
def connections_page():
    return render_template("connections.html", db_path=DB_PATH, console_db=CONSOLE_DB)


@app.get("/backups")
@login_required
def backups_page():
    return render_template("backups.html")


@app.get("/login")
def login():
    if session.get("console_user"):
        return redirect(url_for("overview"))
    return render_template("login.html", need_bootstrap=console_user_count() == 0)


@app.post("/login")
def do_login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    conn = get_console_db()
    user = conn.execute("SELECT * FROM console_users WHERE username=?", (username,)).fetchone()
    conn.close()
    if user is None or not verify_password(password, user["password_hash"]):
        return render_template("login.html", error="Identifiants invalides.", need_bootstrap=False)
    session["console_user"] = user["username"]
    return redirect(url_for("overview"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------------ API
@app.post("/api/console/bootstrap")
def bootstrap():
    if console_user_count() > 0:
        return jsonify({"error": "Un administrateur existe déjà."}), 400
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm") or ""
    if len(username) < 3:
        return jsonify({"error": "Nom d'utilisateur trop court (3 caractères min)."}), 400
    if len(password) < 8:
        return jsonify({"error": "Mot de passe trop court (8 caractères min)."}), 400
    if password != confirm:
        return jsonify({"error": "Les mots de passe ne correspondent pas."}), 400
    conn = get_console_db()
    try:
        conn.execute("INSERT INTO console_users (username, password_hash, created_at) VALUES (?,?,?)",
                     (username, hash_password(password), datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Ce nom d'utilisateur existe déjà."}), 400
    finally:
        conn.close()
    session["console_user"] = username
    return jsonify({"ok": True})


@app.get("/api/console/tables")
@login_required
def api_tables():
    conn = get_db()
    out = [{"name": t, "count": conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]}
           for t in table_names()]
    conn.close()
    return jsonify({"tables": out})


@app.get("/api/console/tables/<table>")
@login_required
def api_table_rows(table):
    if not is_table(table):
        return jsonify({"error": "Table inconnue."}), 404
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(max(int(request.args.get("per_page", 50)), 5), 200)
    except (ValueError, TypeError):
        per_page = 50
    conn = get_db()
    cols = table_info(conn, table)
    rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ? OFFSET ?",
                                          [per_page, (page - 1) * per_page]).fetchall()]
    conn.close()
    return jsonify({"table": table, "columns": cols, "rows": rows, "page": page})


def _coerce(cols, payload):
    data = {}
    for c in cols:
        name = c["name"]
        if c["pk"]:
            continue
        if name in payload:
            data[name] = payload[name]
    return data


@app.post("/api/console/tables/<table>")
@login_required
def api_table_create(table):
    if not is_table(table):
        return jsonify({"error": "Table inconnue."}), 404
    payload = request.get_json(silent=True) or {}
    conn = get_db()
    cols = table_info(conn, table)
    data = _coerce(cols, payload)
    if not data:
        return jsonify({"error": "Aucune colonne à insérer."}), 400
    names = list(data.keys())
    placeholders = ",".join("?" for _ in names)
    try:
        cur = conn.execute(
            f"INSERT INTO {table} ({','.join(names)}) VALUES ({placeholders})",
            list(data.values()))
        conn.commit()
        rid = cur.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()
    return jsonify({"ok": True, "id": rid})


@app.put("/api/console/tables/<table>/<int:rid>")
@login_required
def api_table_update(table, rid):
    if not is_table(table):
        return jsonify({"error": "Table inconnue."}), 404
    payload = request.get_json(silent=True) or {}
    conn = get_db()
    cols = table_info(conn, table)
    pk = next((c["name"] for c in cols if c["pk"]), "id")
    data = _coerce(cols, payload)
    if not data:
        return jsonify({"error": "Aucune modification."}), 400
    sets = ",".join(f"{c}=?" for c in data)
    try:
        conn.execute(f"UPDATE {table} SET {sets} WHERE {pk}=?", list(data.values()) + [rid])
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()
    return jsonify({"ok": True})


@app.delete("/api/console/tables/<table>/<int:rid>")
@login_required
def api_table_delete(table, rid):
    if not is_table(table):
        return jsonify({"error": "Table inconnue."}), 404
    conn = get_db()
    cols = table_info(conn, table)
    pk = next((c["name"] for c in cols if c["pk"]), "id")
    try:
        conn.execute(f"DELETE FROM {table} WHERE {pk}=?", (rid,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()
    return jsonify({"ok": True})


READ_ONLY_RE = re.compile(r"^\s*(SELECT|PRAGMA|EXPLAIN)\b", re.IGNORECASE)


@app.post("/api/console/sql")
@login_required
def api_sql():
    data = request.get_json(silent=True) or {}
    sql = (data.get("sql") or "").strip().rstrip(";")
    if not sql:
        return jsonify({"error": "Requête vide."}), 400
    read_only = bool(READ_ONLY_RE.match(sql))
    conn = get_db()
    try:
        if read_only:
            cur = conn.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = [list(r) for r in cur.fetchall()]
            return jsonify({"ok": True, "read_only": True, "columns": cols, "rows": rows,
                            "count": len(rows)})
        before = conn.total_changes
        cur = conn.execute(sql)
        conn.commit()
        affected = conn.total_changes - before
        return jsonify({"ok": True, "read_only": False, "affected": affected,
                        "rowid": cur.lastrowid})
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


@app.get("/api/console/users")
@login_required
def api_users():
    conn = get_db()
    users = [dict(r) for r in conn.execute("SELECT * FROM users ORDER BY id").fetchall()]
    conn.close()
    return jsonify({"users": users})


@app.post("/api/console/users")
@login_required
def api_user_create():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "user"
    if len(username) < 3:
        return jsonify({"error": "Nom d'utilisateur trop court."}), 400
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Adresse e-mail invalide."}), 400
    if len(password) < 8:
        return jsonify({"error": "Mot de passe trop court (8 caractères min)."}), 400
    if role not in ("admin", "user"):
        role = "user"
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                     (username, email, hash_password(password), role,
                      datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Nom d'utilisateur ou e-mail déjà utilisé."}), 400
    finally:
        conn.close()
    return jsonify({"ok": True})


@app.put("/api/console/users/<int:uid>")
@login_required
def api_user_update(uid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if user is None:
        conn.close()
        return jsonify({"error": "Utilisateur introuvable."}), 404
    sets, params = [], []
    role = data.get("role")
    if role and role in ("admin", "user") and role != user["role"]:
        sets.append("role=?")
        params.append(role)
    password = data.get("password")
    if password:
        if len(password) < 8:
            conn.close()
            return jsonify({"error": "Mot de passe trop court (8 caractères min)."}), 400
        sets.append("password_hash=?")
        params.append(hash_password(password))
    if not sets:
        conn.close()
        return jsonify({"error": "Aucune modification."}), 400
    try:
        conn.execute(f"UPDATE users SET {','.join(sets)} WHERE id=?", params + [uid])
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400
    conn.close()
    return jsonify({"ok": True})


@app.delete("/api/console/users/<int:uid>")
@login_required
def api_user_delete(uid):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if user is None:
        conn.close()
        return jsonify({"error": "Utilisateur introuvable."}), 404
    if user["username"] == session.get("console_user"):
        conn.close()
        return jsonify({"error": "Impossible de supprimer le compte administrateur en cours."}), 400
    try:
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 400
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/console/backup")
@login_required
def api_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"nexfleet_{stamp}.db")
    src = sqlite3.connect(DB_PATH)
    dst = None
    try:
        dst = sqlite3.connect(dest)
        src.backup(dst)
    except Exception as e:
        return jsonify({"error": f"Sauvegarde impossible : {e}"}), 500
    finally:
        if dst:
            dst.close()
        src.close()
    return jsonify({"ok": True, "file": os.path.basename(dest)})


@app.get("/api/console/backups")
@login_required
def api_backups():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    items = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if not f.endswith(".db"):
            continue
        p = os.path.join(BACKUP_DIR, f)
        items.append({"name": f, "size": os.path.getsize(p), "date": datetime.fromtimestamp(os.path.getmtime(p)).isoformat()})
    return jsonify({"backups": items})


@app.get("/api/console/backups/<path:name>/download")
@login_required
def api_backup_download(name):
    if ".." in name or os.path.sep in name or "/" in name:
        abort(400)
    p = os.path.realpath(os.path.join(BACKUP_DIR, name))
    if not p.startswith(os.path.realpath(BACKUP_DIR)):
        abort(403)
    if not os.path.exists(p):
        abort(404)
    return send_file(p, as_attachment=True, download_name=name)


@app.get("/api/console/secret/rotate")
@login_required
def api_secret_rotate():
    backend_secret = os.path.join(BACKEND_DIR, ".secret")
    if os.path.exists(backend_secret):
        os.remove(backend_secret)
    try:
        from auth import SECRET_KEY  # noqa: F401
    except Exception:
        pass
    return jsonify({"ok": True, "note": "Nouvelle clé JWT générée. Toutes les sessions NexFleet sont expirées."})


@app.get("/api/console/health")
@login_required
def api_health():
    return jsonify({"ok": True, "db": DB_PATH, "exists": os.path.exists(DB_PATH),
                    "size": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
