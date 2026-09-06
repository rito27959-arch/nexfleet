@echo off
REM NexFleet Console — gestion de la base et des connexions (port 5001)
cd /d "%~dp0"
if not exist "..\.venv\Scripts\python.exe" (
  echo [ERREUR] Environnement virtuel introuvable. Lancez setup.bat a la racine.
  pause
  exit /b 1
)
echo Demarrage de NexFleet Console sur http://127.0.0.1:5001
start "" http://127.0.0.1:5001
"..\.venv\Scripts\python.exe" wsgi.py
