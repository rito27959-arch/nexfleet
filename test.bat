@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERREUR] Environnement non initialise. Lancez d'abord setup.bat
    pause
    exit /b 1
)
echo ==================================================
echo   NexFleet - Lancement des tests (pytest)
echo ==================================================
".venv\Scripts\python.exe" -m pip install -r backend\requirements-dev.txt >nul
".venv\Scripts\python.exe" -m pytest backend\tests
echo.
if errorlevel 1 (
    echo [ECHEC] Des tests ont echoue.
) else (
    echo [OK] Tous les tests passent.
)
pause
