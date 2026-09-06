# -*- coding: utf-8 -*-
"""Point d'entrée WSGI (waitress) — produit : ``waitress-serve --port=5000 wsgi:app``.

Le fichier app.py est importé tel quel pour que les routes et la base
soient initialisées exactement comme en développement.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app  # noqa: E402

application = app

_HOST = os.environ.get("HOST", "0.0.0.0")
_PORT = int(os.environ.get("PORT", "5000"))

if __name__ == "__main__":
    import waitress

    print(f"NexFleet — serveur waitress démarré sur http://{_HOST}:{_PORT}")
    waitress.serve(app, host=_HOST, port=_PORT, threads=8)
