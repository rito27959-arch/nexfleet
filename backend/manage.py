# -*- coding: utf-8 -*-
"""NexFleet — administration en ligne de commande.

Usage :
    python manage.py list-users
    python manage.py create-admin [--username admin] [--email admin@nexfleet.fr] [--password ...]
    python manage.py set-admin USER
    python manage.py reset-password USER [--password ...]

La commande create-admin crée le compte s'il n'existe pas, sinon réactive le rôle
admin et réinitialise son mot de passe.
"""

import argparse
import getpass
import sys

from auth import hash_password, verify_password
from db import get_db, init_db, now


def _ask_password(explicit):
    if explicit:
        return explicit
    pw = getpass.getpass("Nouveau mot de passe (8 caractères min, avec un chiffre) : ")
    confirm = getpass.getpass("Confirmation : ")
    if pw != confirm:
        print("Erreur : les mots de passe ne correspondent pas.", file=sys.stderr)
        sys.exit(1)
    return pw


def _check_policy(pw):
    if len(pw) < 8:
        print("Erreur : mot de passe trop court (8 caractères minimum).", file=sys.stderr)
        sys.exit(1)
    if not any(c.isdigit() for c in pw):
        print("Erreur : le mot de passe doit contenir au moins un chiffre.", file=sys.stderr)
        sys.exit(1)


def list_users(args):
    init_db()
    db = get_db()
    rows = db.execute("SELECT id, username, email, role FROM users ORDER BY id").fetchall()
    db.close()
    if not rows:
        print("Aucun utilisateur.")
        return
    print(f"{'ID':<4}{'Nom':<22}{'Email':<38}Rôle")
    print("-" * 70)
    for r in rows:
        print(f"{r['id']:<4}{r['username']:<22}{r['email']:<38}{r['role']}")


def create_admin(args):
    init_db()
    username = (args.username or "admin").strip()
    email = (args.email or f"{username}@nexfleet.fr").strip().lower()
    password = _ask_password(args.password)
    _check_policy(password)
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    try:
        if row:
            db.execute("UPDATE users SET role='admin', password_hash=?, email=? WHERE id=?",
                       (hash_password(password), email, row["id"]))
            db.commit()
            print(f"Compte administrateur « {username} » mis à jour (rôle admin, mot de passe réinitialisé).")
        else:
            db.execute("INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                       (username, email, hash_password(password), "admin", now()))
            db.commit()
            print(f"Compte administrateur « {username} » créé.")
    except Exception as e:
        db.rollback()
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def set_admin(args):
    init_db()
    username = (args.username or "").strip()
    if not username:
        print("Erreur : nom d'utilisateur requis.", file=sys.stderr)
        sys.exit(1)
    db = get_db()
    row = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if row is None:
        db.close()
        print(f"Erreur : utilisateur « {username} » introuvable.", file=sys.stderr)
        sys.exit(1)
    db.execute("UPDATE users SET role='admin' WHERE id=?", (row["id"],))
    db.commit()
    db.close()
    print(f"Utilisateur « {username} » promu administrateur.")


def reset_password(args):
    init_db()
    username = (args.username or "").strip()
    if not username:
        print("Erreur : nom d'utilisateur requis.", file=sys.stderr)
        sys.exit(1)
    password = _ask_password(args.password)
    _check_policy(password)
    db = get_db()
    row = db.execute("SELECT id, password_hash FROM users WHERE username=?", (username,)).fetchone()
    if row is None:
        db.close()
        print(f"Erreur : utilisateur « {username} » introuvable.", file=sys.stderr)
        sys.exit(1)
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password), row["id"]))
    db.commit()
    db.close()
    print(f"Mot de passe de « {username} » réinitialisé.")


def main():
    parser = argparse.ArgumentParser(description="NexFleet — administration du compte.")
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list-users", help="liste les comptes")
    p_list.set_defaults(func=list_users)

    p_admin = sub.add_parser("create-admin", help="crée / réactive un compte administrateur")
    p_admin.add_argument("--username", default="admin")
    p_admin.add_argument("--email", default=None)
    p_admin.add_argument("--password", default=None)
    p_admin.set_defaults(func=create_admin)

    p_set = sub.add_parser("set-admin", help="promeut un utilisateur administrateur")
    p_set.add_argument("username")
    p_set.set_defaults(func=set_admin)

    p_reset = sub.add_parser("reset-password", help="réinitialise un mot de passe")
    p_reset.add_argument("username")
    p_reset.add_argument("--password", default=None)
    p_reset.set_defaults(func=reset_password)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
