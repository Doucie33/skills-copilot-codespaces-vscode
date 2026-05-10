@echo off
setlocal EnableDelayedExpansion
title Construction de l'exécutable — Érablière
color 0B

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  CONSTRUCTION EXECUTABLE STANDALONE (.exe)      ║
echo  ║  Aucune installation requise sur l'ordi cible   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Ce processus crée un fichier .exe autonome qui contient
echo  Python + toutes les librairies + l'application.
echo  L'utilisateur n'a besoin d'installer absolument rien.
echo.

:: Vérifier Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python doit etre installe sur CET ordinateur pour compiler.
    echo Telechargez-le sur https://www.python.org/downloads/
    pause
    exit /b 1
)

cd /d "%~dp0.."

echo  Installation de PyInstaller...
pip install pyinstaller --quiet

echo  Installation des dependances de l'app...
pip install flask reportlab Pillow python-dateutil --quiet

echo.
echo  Construction en cours (peut prendre 3-5 minutes)...
echo.

:: Construire l'exécutable avec toutes les ressources
pyinstaller --noconfirm --onedir --windowed ^
    --name "Erabliere" ^
    --icon "static\img\icon.ico" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import "reportlab.graphics" ^
    --hidden-import "reportlab.pdfgen" ^
    --hidden-import "PIL._imaging" ^
    --collect-all "flask" ^
    --collect-all "jinja2" ^
    --collect-all "werkzeug" ^
    app.py 2>nul

:: Si l'icône n'existe pas, reconstruire sans icône
if %errorlevel% neq 0 (
    pyinstaller --noconfirm --onedir --windowed ^
        --name "Erabliere" ^
        --add-data "templates;templates" ^
        --add-data "static;static" ^
        --hidden-import "reportlab.graphics" ^
        --hidden-import "reportlab.pdfgen" ^
        --hidden-import "PIL._imaging" ^
        --collect-all "flask" ^
        --collect-all "jinja2" ^
        --collect-all "werkzeug" ^
        app.py
)

if not exist "dist\Erabliere\Erabliere.exe" (
    echo.
    echo ERREUR lors de la construction.
    pause
    exit /b 1
)

:: Créer le dossier data dans la distribution
mkdir "dist\Erabliere\data" 2>nul
mkdir "dist\Erabliere\data\pdfs" 2>nul

:: Créer le lanceur wrapper
(
echo @echo off
echo cd /d "%%~dp0"
echo start "" "Erabliere.exe"
) > "dist\Erabliere\LANCER.bat"

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  COMPILATION REUSSIE !                          ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║                                                  ║
echo  ║  Dossier : dist\Erabliere\                       ║
echo  ║                                                  ║
echo  ║  Copiez ce dossier sur votre cle USB.            ║
echo  ║  Double-cliquez sur Erabliere.exe pour lancer.   ║
echo  ║                                                  ║
echo  ║  Taille approximative : 50-100 Mo                ║
echo  ║  Aucune installation requise !                   ║
echo  ║                                                  ║
echo  ╚══════════════════════════════════════════════════╝
echo.

explorer dist\Erabliere
pause
