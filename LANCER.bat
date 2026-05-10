@echo off
chcp 65001 > nul
title Érablière — Démarrage...
cd /d "%~dp0"

echo.
echo  ╔════════════════════════════════════════════════╗
echo  ║     ÉRABLIÈRE — Logiciel de gestion           ║
echo  ╚════════════════════════════════════════════════╝
echo.

:: ─── Étape 1 : Vérifier Python ───────────────────────────────────────────────
python --version > nul 2>&1
if not errorlevel 1 goto PYTHON_OK

py --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto PYTHON_OK
)

echo  [!] Python n'est pas installé sur cet ordinateur.
echo.
echo  Installation automatique via Windows Store...
echo  (Si ça ne fonctionne pas, allez sur https://www.python.org/downloads/)
echo.
winget install -e --id Python.Python.3.11 --silent --accept-source-agreements 2> nul
timeout /t 5 /nobreak > nul

python --version > nul 2>&1
if errorlevel 1 (
    echo  [!] Impossible d'installer Python automatiquement.
    echo.
    echo  Veuillez installer Python manuellement :
    echo    1. Ouvrez https://www.python.org/downloads/
    echo    2. Téléchargez et installez Python 3
    echo    3. COCHEZ "Add Python to PATH" pendant l'installation
    echo    4. Relancez LANCER.bat
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

:PYTHON_OK
if not defined PYTHON set PYTHON=python
echo  [✓] Python détecté.

:: ─── Étape 2 : Installer les dépendances (une seule fois) ────────────────────
if exist "erabliere-app\.deps_ok" goto DEPS_OK

echo  [~] Installation des composants (première fois uniquement)...
echo      Patientez quelques secondes...
echo.
%PYTHON% -m pip install flask reportlab Pillow --quiet --user 2>&1
if errorlevel 1 (
    echo  [!] Erreur lors de l'installation des composants.
    echo  Essai avec --break-system-packages...
    %PYTHON% -m pip install flask reportlab Pillow --quiet --break-system-packages 2>&1
)

%PYTHON% -c "import flask" > nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] Impossible d'installer les composants requis.
    echo  Vérifiez votre connexion Internet et réessayez.
    pause
    exit /b 1
)

:: Créer le marqueur pour ne pas réinstaller à chaque fois
echo ok > "erabliere-app\.deps_ok"
echo  [✓] Composants installés.

:DEPS_OK
echo  [✓] Composants prêts.

:: ─── Étape 3 : Créer le dossier data si absent ───────────────────────────────
if not exist "erabliere-app\data" mkdir "erabliere-app\data"
if not exist "erabliere-app\data\pdfs" mkdir "erabliere-app\data\pdfs"

:: ─── Étape 4 : Ouvrir le navigateur après 2 secondes ─────────────────────────
:: (Script VBS pour ouvrir le navigateur sans bloquer)
echo Set WshShell = CreateObject("WScript.Shell") > "%TEMP%\erabliere_open.vbs"
echo WScript.Sleep 2500 >> "%TEMP%\erabliere_open.vbs"
echo WshShell.Run "http://localhost:5000" >> "%TEMP%\erabliere_open.vbs"
start "" /b wscript "%TEMP%\erabliere_open.vbs"

:: ─── Étape 5 : Lancer l'application ─────────────────────────────────────────
echo.
echo  ╔════════════════════════════════════════════════╗
echo  ║   Logiciel démarré !                          ║
echo  ║   Adresse : http://localhost:5000             ║
echo  ║                                               ║
echo  ║   Fermez cette fenêtre pour arrêter.          ║
echo  ╚════════════════════════════════════════════════╝
echo.

cd erabliere-app
%PYTHON% app.py

echo.
echo  Application arrêtée. Appuyez sur une touche pour fermer.
pause > nul
