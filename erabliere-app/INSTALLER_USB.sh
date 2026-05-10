#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  ERABLIERE — Installateur USB universel (Windows + Linux)
#  Lancez ce script UNE SEULE FOIS depuis votre Kubuntu.
#  La clé USB fonctionnera ensuite sur n'importe quel ordinateur.
# ══════════════════════════════════════════════════════════════
clear

VERT='\033[0;32m'
JAUNE='\033[1;33m'
ROUGE='\033[0;31m'
GRAS='\033[1m'
NC='\033[0m'

banner() {
    clear
    echo ""
    echo -e "${VERT}  ╔══════════════════════════════════════════════╗${NC}"
    echo -e "${VERT}  ║   ÉRABLIÈRE — Installation clé USB          ║${NC}"
    echo -e "${VERT}  ║   Compatible Windows ET Linux               ║${NC}"
    echo -e "${VERT}  ╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

banner
echo -e "  Ce programme prépare votre clé USB pour fonctionner"
echo -e "  sur ${GRAS}n'importe quel ordinateur Windows ou Linux${NC}."
echo ""
echo "  Vous avez besoin de :"
echo "    ✓ Votre clé USB branchée"
echo "    ✓ Une connexion Internet (une seule fois)"
echo ""
read -p "  Appuyez sur Entrée pour commencer..."

# ── ÉTAPE 1 : Trouver la clé USB ─────────────────────────────────────────────
banner
echo -e "${GRAS}  ÉTAPE 1 — Sélectionner la clé USB${NC}"
echo ""
echo "  Clés USB détectées :"
echo ""

# Lister les clés dans /media/$USER/
if ls /media/$USER/ &>/dev/null; then
    for cle in /media/$USER/*/; do
        TAILLE=$(df -h "$cle" 2>/dev/null | awk 'NR==2{print $2}')
        LIBRE=$(df -h "$cle" 2>/dev/null | awk 'NR==2{print $4}')
        echo "    📦 $cle   ($TAILLE total, $LIBRE libre)"
    done
else
    echo "    Aucune clé détectée dans /media/$USER/"
    echo "    Branchez votre clé USB et réessayez."
    read -p "  Appuyez sur Entrée..."
    exit 1
fi

echo ""
echo -e "  ${JAUNE}Copiez-collez le chemin complet de votre clé ci-dessus.${NC}"
echo ""
read -p "  Chemin de la clé USB : " USB_MOUNT

# Enlever le / final s'il y en a un
USB_MOUNT="${USB_MOUNT%/}"

if [ ! -d "$USB_MOUNT" ]; then
    echo ""
    echo -e "  ${ROUGE}ERREUR : Ce chemin n'existe pas.${NC}"
    echo "  Vérifiez que la clé est bien branchée."
    read -p "  Appuyez sur Entrée..."
    exit 1
fi

# Vérifier l'espace libre (besoin d'environ 400 Mo)
LIBRE_MO=$(df -m "$USB_MOUNT" 2>/dev/null | awk 'NR==2{print $4}')
if [ -n "$LIBRE_MO" ] && [ "$LIBRE_MO" -lt 300 ]; then
    echo ""
    echo -e "  ${ROUGE}ATTENTION : Seulement ${LIBRE_MO} Mo libres sur la clé.${NC}"
    echo "  Il faut au moins 400 Mo d'espace libre."
    read -p "  Continuer quand même ? (o/n) : " FORCE
    [[ "$FORCE" != "o" && "$FORCE" != "O" ]] && exit 0
fi

DEST="$USB_MOUNT/Erabliere"

echo ""
echo -e "  Le logiciel sera installé dans :"
echo -e "  ${GRAS}$DEST${NC}"
echo ""
read -p "  Confirmer l'installation ? (o/n) : " OK
[[ "$OK" != "o" && "$OK" != "O" ]] && { echo "  Annulé."; exit 0; }

# ── ÉTAPE 2 : Créer la structure ──────────────────────────────────────────────
banner
echo -e "${GRAS}  ÉTAPE 2 — Préparation de la clé USB${NC}"
echo ""
echo "  Création des dossiers..."

mkdir -p "$DEST/app/static/uploads"
mkdir -p "$DEST/app/templates"
mkdir -p "$DEST/data/pdfs"
mkdir -p "$DEST/libs_linux"
mkdir -p "$DEST/libs_win"
mkdir -p "$DEST/python_win"

# Copier l'application
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SRC/app.py" ]; then
    echo -e "  ${ROUGE}ERREUR : Fichiers du logiciel introuvables.${NC}"
    echo "  Assurez-vous de lancer ce script depuis le dossier erabliere-app/"
    read -p "  Appuyez sur Entrée..."
    exit 1
fi

cp -r "$SRC/static"    "$DEST/app/"    2>/dev/null
cp -r "$SRC/templates" "$DEST/app/"    2>/dev/null
cp    "$SRC/app.py"    "$DEST/app/"    2>/dev/null

echo "  ✓ Fichiers copiés"

# ── ÉTAPE 3 : Télécharger Python pour Windows ─────────────────────────────────
banner
echo -e "${GRAS}  ÉTAPE 3 — Téléchargement de Python pour Windows${NC}"
echo ""
echo "  Téléchargement en cours... (15-30 secondes)"
echo ""

PY_URL="https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip"
PY_ZIP="/tmp/erabliere_python_win.zip"

# Téléchargement avec barre de progression
if command -v wget &>/dev/null; then
    wget -q --show-progress "$PY_URL" -O "$PY_ZIP" 2>&1
elif command -v curl &>/dev/null; then
    curl -L --progress-bar "$PY_URL" -o "$PY_ZIP"
fi

if [ ! -f "$PY_ZIP" ] || [ ! -s "$PY_ZIP" ]; then
    echo -e "  ${ROUGE}ERREUR : Impossible de télécharger Python.${NC}"
    echo "  Vérifiez votre connexion Internet."
    read -p "  Appuyez sur Entrée..."
    exit 1
fi

echo ""
echo "  Extraction de Python pour Windows..."
unzip -q "$PY_ZIP" -d "$DEST/python_win/"
rm -f "$PY_ZIP"

# Activer site-packages dans Python Windows embarqué
PTH_FILE=$(find "$DEST/python_win/" -name "python3*._pth" 2>/dev/null | head -1)
if [ -n "$PTH_FILE" ]; then
    # Activer import site
    sed -i 's/#import site/import site/' "$PTH_FILE" 2>/dev/null
    # Ajouter le chemin libs_win (relatif, avec variable)
    grep -q "libs_win" "$PTH_FILE" 2>/dev/null || echo "..\libs_win" >> "$PTH_FILE"
fi

# Télécharger get-pip.py (sera utilisé au 1er lancement Windows)
echo "  Téléchargement de pip pour Windows..."
GET_PIP="/tmp/get-pip.py"
if command -v wget &>/dev/null; then
    wget -q "https://bootstrap.pypa.io/get-pip.py" -O "$GET_PIP" 2>/dev/null
elif command -v curl &>/dev/null; then
    curl -sL "https://bootstrap.pypa.io/get-pip.py" -o "$GET_PIP"
fi
[ -f "$GET_PIP" ] && cp "$GET_PIP" "$DEST/python_win/get-pip.py"

echo "  ✓ Python Windows prêt"

# ── ÉTAPE 4 : Installer les paquets Linux ─────────────────────────────────────
banner
echo -e "${GRAS}  ÉTAPE 4 — Installation des composants Linux${NC}"
echo ""
echo "  Installation de Flask, PDF, images..."
echo "  (2-3 minutes selon votre connexion)"
echo ""

# Vérifier pip
if ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
    echo "  Installation de pip..."
    sudo apt install -y python3-pip &>/dev/null || true
fi

PIP=$(command -v pip3 || command -v pip)

"$PIP" install flask reportlab Pillow python-dateutil \
    --target "$DEST/libs_linux" \
    --quiet --no-warn-script-location 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "  ${JAUNE}Tentative avec pip3 install...${NC}"
    python3 -m pip install flask reportlab Pillow python-dateutil \
        --target "$DEST/libs_linux" \
        --quiet 2>/dev/null
fi

echo "  ✓ Composants Linux installés"

# ── ÉTAPE 5 : Créer les lanceurs ──────────────────────────────────────────────
banner
echo -e "${GRAS}  ÉTAPE 5 — Création des lanceurs${NC}"
echo ""

# ── Lanceur Windows ───────────────────────────────────────────────────────────
cat > "$DEST/LANCER_WINDOWS.bat" << 'EOF'
@echo off
title Erabliere - Demarrage...
color 0A
cls

echo.
echo  ==========================================
echo    ERABLIERE - Gestion d'erabliere
echo  ==========================================
echo.

set DIR=%~dp0
set PYTHON=%DIR%python_win\python.exe
set LIBS=%DIR%libs_win
set APP=%DIR%app

:: Verifier que Python est present
if not exist "%PYTHON%" (
    echo  ERREUR: Python introuvable sur la cle USB.
    echo  Reinstallez le logiciel.
    pause
    exit /b 1
)

:: Premier lancement Windows : installer les composants
if not exist "%LIBS%\flask" (
    echo  Premier lancement - Configuration automatique...
    echo  Connexion Internet requise une seule fois.
    echo.

    :: Installer pip si necessaire
    if exist "%DIR%python_win\get-pip.py" (
        "%PYTHON%" "%DIR%python_win\get-pip.py" --no-warn-script-location --quiet 2>nul
    )

    :: Installer les composants Windows
    echo  Installation de Flask, PDF, images...
    "%PYTHON%" -m pip install flask reportlab Pillow python-dateutil ^
        --target "%LIBS%" --no-warn-script-location --quiet

    if errorlevel 1 (
        echo.
        echo  ERREUR lors de l'installation.
        echo  Verifiez votre connexion Internet.
        pause
        exit /b 1
    )
    echo  Configuration terminee !
    echo.
)

:: Demarrer le logiciel
echo  Demarrage du logiciel...
echo  Le navigateur va s'ouvrir automatiquement.
echo  Ne fermez pas cette fenetre pendant l'utilisation.
echo.
echo  Pour quitter : appuyez sur Ctrl+C
echo  ==========================================
echo.

cd /d "%APP%"
set PYTHONPATH=%LIBS%
set PYTHONHOME=
"%PYTHON%" app.py

echo.
echo  Logiciel ferme.
echo  Vous pouvez retirer la cle USB en toute securite.
pause
EOF

# ── Lanceur Linux ─────────────────────────────────────────────────────────────
cat > "$DEST/LANCER_LINUX.sh" << 'LINUXEOF'
#!/bin/bash
# Lanceur Linux — Érablière
clear
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIBS="$SCRIPT_DIR/libs_linux"
APP="$SCRIPT_DIR/app"

echo ""
echo "  =========================================="
echo "    ÉRABLIÈRE — Gestion d'érablière"
echo "  =========================================="
echo ""

# Premier lancement sur un nouvel ordinateur Linux
if [ ! -d "$LIBS/flask" ]; then
    echo "  Premier lancement — Configuration automatique..."
    echo "  Connexion Internet requise une seule fois."
    echo ""

    if ! command -v python3 &>/dev/null; then
        echo "  ERREUR : python3 est requis."
        echo "  Installez-le : sudo apt install python3 python3-pip"
        read -p "  Appuyez sur Entrée..."
        exit 1
    fi

    mkdir -p "$LIBS"
    python3 -m pip install flask reportlab Pillow python-dateutil \
        --target "$LIBS" --quiet 2>/dev/null || \
    pip3 install flask reportlab Pillow python-dateutil \
        --target "$LIBS" --quiet 2>/dev/null

    echo "  ✓ Configuration terminée !"
    echo ""
fi

# Démarrer le logiciel
echo "  Démarrage en cours..."
echo "  Le navigateur va s'ouvrir automatiquement."
echo ""
echo "  Pour quitter : Ctrl+C"
echo "  =========================================="
echo ""

cd "$APP"
export PYTHONPATH="$LIBS"
python3 app.py

echo ""
echo "  Logiciel fermé."
echo "  Vous pouvez retirer la clé USB en toute sécurité."
LINUXEOF

chmod +x "$DEST/LANCER_LINUX.sh"

# Raccourci double-clic pour Dolphin (Kubuntu)
cat > "$DEST/Erabliere.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Érablière
Comment=Logiciel de gestion d'érablière
Exec=bash -c 'cd "%DEST%" && ./LANCER_LINUX.sh'
Icon=applications-office
Terminal=true
Categories=Office;
EOF
chmod +x "$DEST/Erabliere.desktop"

# Fichier LIRE_MOI
cat > "$DEST/LIRE_MOI.txt" << 'README'
ÉRABLIÈRE — Logiciel de gestion portable
==========================================

WINDOWS : Double-cliquez sur  LANCER_WINDOWS.bat
LINUX   : Double-cliquez sur  LANCER_LINUX.sh
          OU ouvrez un terminal et tapez : ./LANCER_LINUX.sh

NOTE : Au premier démarrage sur un nouvel ordinateur,
       une connexion Internet est requise (2 min).
       Les fois suivantes, aucune connexion nécessaire.

VOS DONNÉES sont dans le dossier : data/
→ Sauvegardez ce dossier régulièrement !

Accès : http://localhost:5000
README

echo "  ✓ Lanceurs créés"

# ── TERMINÉ ───────────────────────────────────────────────────────────────────
banner
echo -e "${GRAS}  INSTALLATION TERMINÉE !${NC}"
echo ""
echo "  Votre clé USB est prête."
echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │  WINDOWS : LANCER_WINDOWS.bat           │"
echo "  │  LINUX   : LANCER_LINUX.sh              │"
echo "  └─────────────────────────────────────────┘"
echo ""
echo "  Vos données seront dans :"
echo "  $DEST/data/"
echo ""
echo -e "  ${JAUNE}Sauvegardez ce dossier régulièrement !${NC}"
echo ""
# Ouvrir le gestionnaire de fichiers sur la clé
xdg-open "$DEST" 2>/dev/null &
