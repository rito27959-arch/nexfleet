@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERREUR] Environnement non initialise.
    echo Lancez d'abord setup.bat
    pause
    exit /b 1
)
echo.
echo   NexFleet demarre sur  http://127.0.0.1:5000
echo   (serveur waitress - arret avec Ctrl+C)
echo.
start "" http://127.0.0.1:5000
".venv\Scripts\python.exe" backend\wsgi.py
pause
