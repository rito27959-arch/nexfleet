@echo off
setlocal
cd /d "%~dp0"
echo ==================================================
echo   NexFleet - Installation de l'environnement
echo ==================================================
echo.

rem --- Detection de Python (fiable meme si PATH pas rafraichi) ---
set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
    for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"
)
if not defined PY goto :nopython

rem --- Creation du venv ---
if not exist ".venv\Scripts\python.exe" (
    echo Creation de l'environnement virtuel...
    "%PY%" -m venv .venv
    if errorlevel 1 goto :venvfail
)
echo Installation des dependances Python...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 goto :pipfail
echo.
echo ==================================================
echo   Installation terminee. Lancez maintenant run.bat
echo ==================================================
pause
exit /b 0

:nopython
echo [ERREUR] Python introuvable sur ce systeme.
echo.
echo Installez Python 3.9+ depuis https://www.python.org/downloads/
echo IMPORTANT: cochez la case "Add Python to PATH" pendant l'installation,
echo puis relancez ce script.
pause
exit /b 1

:venvfail
echo [ERREUR] Impossible de creer l'environnement virtuel.
echo.
echo Si vous etes sous Windows 10/11, la commande "python" peut etre un
echo raccourci vers le Microsoft Store, pas un vrai Python.
echo.
echo 1. Ouvrez Parametres - Applications - Parametres avances
echo    - Alias d'execution des applications.
echo 2. Desactivez "python.exe" et "python3.exe".
echo 3. Installez Python 3.9+ depuis https://www.python.org/downloads/
echo    en cochant "Add Python to PATH".
echo 4. Relancez ce script.
pause
exit /b 1

:pipfail
echo [ERREUR] Echec de l'installation des dependances.
echo Verifiez votre connexion internet puis relancez ce script.
pause
exit /b 1
