# -*- coding: utf-8 -*-
"""NexFleet Console — gestion de la base et des connexions.
Démarrage :  python app.py   (http://127.0.0.1:5001)
"""
import sys
from waitress import serve

import app as console_app

if __name__ == "__main__":
    print("NexFleet Console : http://127.0.0.1:5001")
    serve(console_app.app, host="127.0.0.1", port=5001)
