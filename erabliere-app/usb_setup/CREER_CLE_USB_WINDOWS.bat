@echo off
setlocal EnableDelayedExpansion
title Création de la clé USB portable — Érablière
color 0A

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║    CREATION DE LA CLE USB PORTABLE              ║
echo  ║    Logiciel de gestion d'Erabliere              ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ── Vérifier que ce script est lancé depuis le bon dossier ──────────────────
if not exist "..\app.py" (
    echo ERREUR: Lancez ce script depuis le dossier usb_setup\
    echo        en etant dans le repertoire erabliere-app\
    pause
    exit /b 1
)

:: ── Choisir la lettre de la clé USB ─────────────────────────────────────────
echo  Lecteurs disponibles :
echo.
wmic logicaldisk get caption,description,drivetype 2>nul | findstr /i "Removable\|2 "
echo.
set /p USB_DRIVE="  Entrez la lettre de votre cle USB (ex: E, F, G) : "
set USB_DRIVE=%USB_DRIVE%:

if not exist "%USB_DRIVE%\" (
    echo.
    echo ERREUR : Le lecteur %USB_DRIVE% n'existe pas.
    pause
    exit /b 1
)

echo.
echo  Cible : %USB_DRIVE%\Erabliere\
echo.
echo  ATTENTION : Cette operation va copier ~200 Mo sur la cle USB.
set /p CONFIRM="  Confirmer? (O/N) : "
if /i not "%CONFIRM%"=="O" exit /b 0

:: ── Créer la structure de dossiers ──────────────────────────────────────────
echo.
echo  [1/5] Creation de la structure de dossiers...
set APP_DIR=%USB_DRIVE%\Erabliere
mkdir "%APP_DIR%"              2>nul
mkdir "%APP_DIR%\app"          2>nul
mkdir "%APP_DIR%\app\static"   2>nul
mkdir "%APP_DIR%\app\templates" 2>nul
mkdir "%APP_DIR%\python"       2>nul
mkdir "%APP_DIR%\data"         2>nul
mkdir "%APP_DIR%\data\pdfs"    2>nul

:: ── Télécharger Python portable ──────────────────────────────────────────────
echo  [2/5] Telechargement de Python portable (64-bit)...
set PY_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip
set PY_ZIP=%TEMP%\python-embed.zip

powershell -Command "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%'}" 2>nul
if not exist "%PY_ZIP%" (
    echo ERREUR: Impossible de telecharger Python. Verifiez votre connexion.
    pause
    exit /b 1
)

echo  Extraction de Python...
powershell -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%APP_DIR%\python' -Force" 2>nul
del "%PY_ZIP%"

:: ── Activer pip dans Python embarqué ─────────────────────────────────────────
echo  [3/5] Installation de pip...

:: Modifier python312._pth pour activer les imports de site-packages
set PTH_FILE=%APP_DIR%\python\python312._pth
if exist "%APP_DIR%\python\python312._pth" (
    type "%APP_DIR%\python\python312._pth" | findstr /v "^#import site" > "%TEMP%\pth_tmp.txt"
    echo import site >> "%TEMP%\pth_tmp.txt"
    copy /y "%TEMP%\pth_tmp.txt" "%APP_DIR%\python\python312._pth" >nul
)

:: Télécharger get-pip.py
set GETPIP=%TEMP%\get-pip.py
powershell -Command "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%'}" 2>nul

if exist "%GETPIP%" (
    "%APP_DIR%\python\python.exe" "%GETPIP%" --no-warn-script-location --quiet
    del "%GETPIP%"
)

:: ── Installer les dépendances ────────────────────────────────────────────────
echo  [4/5] Installation des dependances Python...
echo       (Flask, ReportLab, Pillow — cela peut prendre quelques minutes)

"%APP_DIR%\python\python.exe" -m pip install flask reportlab Pillow python-dateutil ^
    --no-warn-script-location --quiet --target "%APP_DIR%\python\Lib\site-packages"

:: ── Copier l'application ─────────────────────────────────────────────────────
echo  [5/5] Copie de l'application...
xcopy /E /I /Y "..\static"    "%APP_DIR%\app\static"    >nul
xcopy /E /I /Y "..\templates" "%APP_DIR%\app\templates" >nul
copy /Y "..\app.py"           "%APP_DIR%\app\app.py"    >nul

:: ── Créer le lanceur principal ───────────────────────────────────────────────
echo  Creation du lanceur...

(
echo @echo off
echo title Erabliere — Gestion d'erabliere
echo cd /d "%%~dp0app"
echo set PYTHONPATH=%%~dp0python\Lib\site-packages
echo set PYTHONHOME=
echo start "" "%%~dp0python\python.exe" app.py
echo exit
) > "%APP_DIR%\LANCER_ERABLIERE.bat"

:: Lanceur avec fenêtre visible (pour debug)
(
echo @echo off
echo title Erabliere — Serveur
echo color 0A
echo cd /d "%%~dp0app"
echo set PYTHONPATH=%%~dp0python\Lib\site-packages
echo set PYTHONHOME=
echo echo Demarrage du logiciel Erabliere...
echo echo Le navigateur va s'ouvrir automatiquement.
echo echo Appuyez sur Ctrl+C pour quitter.
echo echo.
echo "%%~dp0python\python.exe" app.py
echo pause
) > "%APP_DIR%\LANCER_AVEC_CONSOLE.bat"

:: ── Fichier README ───────────────────────────────────────────────────────────
(
echo ERABLIERE — Logiciel de gestion portable
echo ==========================================
echo.
echo UTILISATION :
echo   Double-cliquer sur : LANCER_ERABLIERE.bat
echo.
echo   Le navigateur s'ouvre automatiquement sur http://localhost:5000
echo.
echo VOS DONNEES :
echo   Toutes vos donnees sont dans le dossier : data\
echo   Fichier base de donnees : data\erabliere.db
echo   Sauvegardez ce dossier regulierement !
echo.
echo COMPATIBLE : Windows 10 et 11 (64-bit)
) > "%APP_DIR%\LIRE_MOI.txt"

:: ── Résumé ───────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  INSTALLATION TERMINEE AVEC SUCCES !            ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║                                                  ║
echo  ║  Emplacement : %APP_DIR%\
echo  ║                                                  ║
echo  ║  Pour lancer :                                   ║
echo  ║    Double-clic sur LANCER_ERABLIERE.bat          ║
echo  ║                                                  ║
echo  ║  Vos donnees sont dans : data\                   ║
echo  ║  Sauvegardez ce dossier !                        ║
echo  ║                                                  ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
