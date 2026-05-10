@echo off
title Érablière - Logiciel de gestion
echo ========================================
echo   ERABLIERE - Logiciel de gestion
echo ========================================
echo.

:: Check Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe.
    echo Telechargez Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install dependencies
echo Installation des dependances...
pip install flask reportlab Pillow python-dateutil --quiet

echo.
echo Demarrage du serveur...
echo Ouvrez votre navigateur a l'adresse: http://localhost:5000
echo Appuyez sur Ctrl+C pour arreter le serveur.
echo.

:: Open browser after 2 seconds
start /b timeout /t 2 /nobreak > nul && start http://localhost:5000

python app.py

pause
