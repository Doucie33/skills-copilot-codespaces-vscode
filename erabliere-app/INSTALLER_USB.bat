@echo off
setlocal EnableDelayedExpansion
title Installation Erabliere sur cle USB
color 0A
mode con: cols=60 lines=35

cls
echo.
echo  ==========================================
echo    ERABLIERE - Installation sur cle USB
echo  ==========================================
echo.
echo  Ce programme va installer le logiciel
echo  directement sur votre cle USB.
echo.
echo  Vous aurez besoin de :
echo    - Votre cle USB branchee
echo    - Une connexion Internet (1 seule fois)
echo.
echo  ==========================================
echo.
pause

:: ════════════════════════════════════════════
::  ETAPE 1 : Trouver la cle USB
:: ════════════════════════════════════════════
cls
echo.
echo  ==========================================
echo   ETAPE 1 sur 3 : Choisir la cle USB
echo  ==========================================
echo.
echo  Lecteurs detectes sur cet ordinateur :
echo.

for %%d in (D E F G H I J K L M N) do (
    if exist "%%d:\" (
        for /f "tokens=*" %%v in ('vol %%d: 2^>nul ^| findstr /i "Volume"') do (
            echo    %%d:  %%v
        )
    )
)

echo.
set /p LETTRE="  Tapez la lettre de votre cle USB (ex: E) : "
set LETTRE=%LETTRE: =%
set USB=%LETTRE%:

if not exist "%USB%\" (
    echo.
    echo  ERREUR : La lettre %USB% n'existe pas.
    echo  Verifiez que votre cle est bien branchee.
    echo.
    pause
    exit /b 1
)

:: Verifier l'espace disponible (besoin de ~300 Mo)
for /f "tokens=3" %%a in ('dir %USB% 2^>nul ^| findstr /i "available\|disponible\|libre"') do set LIBRE=%%a

echo.
echo  Cle USB selectionnee : %USB%
echo.
echo  Le logiciel sera installe dans : %USB%\Erabliere\
echo.
set /p OK="  Confirmer ? Tapez O puis Entree : "
if /i not "%OK%"=="O" (
    echo  Installation annulee.
    pause
    exit /b 0
)

set DEST=%USB%\Erabliere

:: ════════════════════════════════════════════
::  ETAPE 2 : Telecharger Python
:: ════════════════════════════════════════════
cls
echo.
echo  ==========================================
echo   ETAPE 2 sur 3 : Telechargement de Python
echo  ==========================================
echo.
echo  Telechargement de Python portable...
echo  (inclus directement dans le logiciel)
echo.
echo  Cela peut prendre 2 a 5 minutes selon
echo  votre connexion Internet.
echo.

:: Creer la structure de dossiers
mkdir "%DEST%\app\static\uploads" 2>nul
mkdir "%DEST%\app\templates"      2>nul
mkdir "%DEST%\python"             2>nul
mkdir "%DEST%\data\pdfs"          2>nul
mkdir "%DEST%\libs"               2>nul

:: Telecharger Python portable via PowerShell
set PY_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip
set PY_ZIP=%TEMP%\erabliere_python.zip

echo  [1/4] Telechargement de Python...
powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue';" ^
  "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%'" 2>nul

if not exist "%PY_ZIP%" (
    echo.
    echo  ERREUR : Impossible de telecharger Python.
    echo  Verifiez votre connexion Internet.
    pause
    exit /b 1
)

echo  [2/4] Installation de Python sur la cle...
powershell -NoProfile -Command ^
  "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%DEST%\python' -Force" 2>nul
del "%PY_ZIP%"

:: Activer les packages dans Python embarque
echo  [3/4] Configuration de Python...
set PTH=
for %%f in ("%DEST%\python\python3*._pth") do set PTH=%%f
if defined PTH (
    type "%PTH%" | findstr /v "^#import site" > "%TEMP%\pth_new.txt" 2>nul
    echo import site>> "%TEMP%\pth_new.txt"
    copy /y "%TEMP%\pth_new.txt" "%PTH%" >nul 2>nul
    del "%TEMP%\pth_new.txt" 2>nul
)

:: Telecharger et installer pip
echo  [4/4] Installation du gestionnaire de paquets...
set GETPIP=%TEMP%\get-pip.py
powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue';" ^
  "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%'" 2>nul

if exist "%GETPIP%" (
    "%DEST%\python\python.exe" "%GETPIP%" ^
      --no-warn-script-location --quiet 2>nul
    del "%GETPIP%"
)

:: ════════════════════════════════════════════
::  ETAPE 3 : Installer les composants
:: ════════════════════════════════════════════
cls
echo.
echo  ==========================================
echo   ETAPE 3 sur 3 : Installation du logiciel
echo  ==========================================
echo.
echo  Installation des composants...
echo  (Flask, PDF, images - quelques minutes)
echo.

"%DEST%\python\python.exe" -m pip install ^
    flask reportlab Pillow python-dateutil ^
    --target "%DEST%\libs" ^
    --no-warn-script-location --quiet 2>nul

if %errorlevel% neq 0 (
    :: Essai avec une autre methode
    "%DEST%\python\python.exe" -m pip install ^
        flask reportlab Pillow python-dateutil ^
        --no-warn-script-location -q
)

echo  Copie du logiciel sur la cle...

:: Copier l'application depuis le dossier du script installateur
set SRC=%~dp0

:: Chercher les fichiers sources (le script est dans erabliere-app\)
if exist "%SRC%app.py" (
    set APP_SRC=%SRC%
) else if exist "%SRC%..\app.py" (
    set APP_SRC=%SRC%..\
) else (
    echo  ERREUR: Fichiers du logiciel introuvables.
    echo  Assurez-vous que INSTALLER_USB.bat est dans
    echo  le dossier erabliere-app\
    pause
    exit /b 1
)

xcopy /E /I /Y "%APP_SRC%static"    "%DEST%\app\static"    >nul 2>nul
xcopy /E /I /Y "%APP_SRC%templates" "%DEST%\app\templates" >nul 2>nul
copy  /Y       "%APP_SRC%app.py"    "%DEST%\app\app.py"    >nul 2>nul

:: ════════════════════════════════════════════
::  Creer le lanceur Windows (sur la cle)
:: ════════════════════════════════════════════
(
echo @echo off
echo title Erabliere - En cours...
echo color 0A
echo cls
echo echo.
echo echo  ==========================================
echo echo    ERABLIERE - Demarrage en cours...
echo echo  ==========================================
echo echo.
echo echo  Le navigateur va s'ouvrir dans 3 secondes.
echo echo  Ne fermez pas cette fenetre pendant l'utilisation.
echo echo.
echo echo  Pour quitter : appuyez sur Ctrl+C
echo echo  ==========================================
echo.
echo cd /d "%%~dp0app"
echo set PYTHONPATH=%%~dp0libs;%%~dp0python\Lib\site-packages
echo set PYTHONHOME=
echo "%%~dp0python\python.exe" app.py
echo echo.
echo echo Logiciel ferme. Vous pouvez retirer la cle USB.
echo pause
) > "%DEST%\LANCER_WINDOWS.bat"

:: ════════════════════════════════════════════
::  Creer le lanceur Linux (sur la cle)
:: ════════════════════════════════════════════
(
echo #!/bin/bash
echo # Lanceur Erabliere pour Linux
echo SCRIPT_DIR="$^(cd "$^(dirname "${BASH_SOURCE[0]}"^)" ^&^& pwd^)"
echo LIBS="$SCRIPT_DIR/libs_linux"
echo.
echo # Premiere utilisation : installer les paquets
echo if [ ! -d "$LIBS" ]; then
echo   echo "Premiere utilisation - Installation automatique ^(1-2 min^)..."
echo   if ! command -v python3 ^&^>/dev/null; then
echo     echo "ERREUR: python3 est requis sur Linux."
echo     echo "Installez-le: sudo apt install python3 python3-pip"
echo     read -p "Appuyez sur Entree..."
echo     exit 1
echo   fi
echo   mkdir -p "$LIBS"
echo   python3 -m pip install flask reportlab Pillow python-dateutil \
echo     --target "$LIBS" --quiet 2^>/dev/null ^|^| \
echo   pip3 install flask reportlab Pillow python-dateutil \
echo     --target "$LIBS" --quiet
echo   echo "Installation terminee !"
echo fi
echo.
echo cd "$SCRIPT_DIR/app"
echo export PYTHONPATH="$LIBS"
echo echo "Demarrage... Le navigateur va s'ouvrir."
echo python3 app.py
) > "%DEST%\LANCER_LINUX.sh"

:: Forcer les fins de ligne Unix pour le script Linux
powershell -NoProfile -Command ^
  "(Get-Content '%DEST%\LANCER_LINUX.sh') -join \"`n\" | Set-Content '%DEST%\LANCER_LINUX.sh' -NoNewline" 2>nul

:: Creer le fichier LIRE_MOI
(
echo ERABLIERE - Logiciel de gestion d'erabliere
echo =============================================
echo.
echo WINDOWS : Double-cliquez sur LANCER_WINDOWS.bat
echo LINUX   : Ouvrez un terminal ici et tapez :
echo             chmod +x LANCER_LINUX.sh
echo             ./LANCER_LINUX.sh
echo.
echo VOS DONNEES sont dans le dossier : data\
echo SAUVEGARDEZ ce dossier regulierement !
echo.
echo Adresse du logiciel : http://localhost:5000
) > "%DEST%\LIRE_MOI.txt"

:: ════════════════════════════════════════════
::  TERMINE !
:: ════════════════════════════════════════════
cls
echo.
echo  ==========================================
echo.
echo    INSTALLATION TERMINEE !
echo.
echo  ==========================================
echo.
echo  Votre logiciel est pret sur : %USB%\Erabliere\
echo.
echo  POUR UTILISER LE LOGICIEL :
echo.
echo  Sur Windows :
echo    Double-cliquer sur LANCER_WINDOWS.bat
echo.
echo  Sur Linux :
echo    Ouvrir un terminal dans le dossier
echo    Erabliere et taper :
echo      ./LANCER_LINUX.sh
echo.
echo  ==========================================
echo.
echo  VOS DONNEES sont dans le dossier :
echo  %DEST%\data\
echo  Sauvegardez ce dossier regulierement !
echo.
echo  ==========================================
echo.

:: Ouvrir le dossier de la cle USB
explorer "%DEST%"

pause
