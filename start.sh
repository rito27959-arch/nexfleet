#!/usr/bin/env sh
# Nexus de démarrage pour l'hébergement cloud (Render, Koyeb, Railway…).
# Le port est fourni par la plateforme via la variable d'environnement PORT.
set -e
cd backend
exec waitress-serve --host=0.0.0.0 --port="${PORT:-10000}" --threads=8 wsgi:app