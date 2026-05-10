#!/bin/bash
# ══════════════════════════════════════════════
#  ERABLIERE - Installation sur cle USB (Linux)
# ══════════════════════════════════════════════
clear

echo ""
echo "  =========================================="
echo "    ERABLIERE - Installation sur clé USB"
echo "  =========================================="
echo ""
echo "  Ce programme installe le logiciel sur"
echo "  votre clé USB. Connexion Internet requise."
echo ""
read -p "  Appuyez sur Entrée pour continuer..."

# ── Trouver la clé USB ──────────────────────────
clear
echo ""
echo "  =========================================="
echo "   ÉTAPE 1 : Choisir la clé USB"
echo "  =========================================="
echo ""
echo "  Clés USB détectées :"
echo ""
lsblk -o NAME,SIZE,MOUNTPOINT,LABEL 2>/dev/null | grep -v "^loop" | head -20
echo ""
echo "  Cherchez votre clé dans : /media/$USER/"
ls /media/$USER/ 2>/dev/null && echo "" || echo "  (aucune clé détectée dans /media/$USER/)"
echo ""
read -p "  Chemin complet de la clé USB (ex: /media/$USER/MACLÉ) : " USB_MOUNT

if [ ! -d "$USB_MOUNT" ]; then
    echo ""
    echo "  ERREUR : Ce chemin n'existe pas."
    echo "  Vérifiez que la clé est bien branchée."
    read -p "  Appuyez sur Entrée..."
    exit 1
fi

DEST="$USB_MOUNT/Erabliere"
echo ""
echo "  Installation dans : $DEST"
echo ""
read -p "  Confirmer ? (o/n) : " OK
if [[ "$OK" != "o" && "$OK" != "O" ]]; then
    echo "  Installation annulée."
    exit 0
fi

# ── Vérifier Python3 ────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo ""
    echo "  ERREUR : python3 est requis pour l'installation."
    echo "  Installez-le : sudo apt install python3 python3-pip"
    read -p "  Appuyez sur Entrée..."
    exit 1
fi

# ── Créer la structure ──────────────────────────
clear
echo ""
echo "  =========================================="
echo "   ÉTAPE 2 : Installation du logiciel"
echo "  =========================================="
echo ""

mkdir -p "$DEST/app/static/uploads"
mkdir -p "$DEST/app/templates"
mkdir -p "$DEST/data/pdfs"
mkdir -p "$DEST/libs_linux"

# ── Installer les paquets dans libs_linux ───────
echo "  [1/3] Installation des composants..."
echo "        (quelques minutes selon la connexion)"
echo ""

python3 -m pip install flask reportlab Pillow python-dateutil \
    --target "$DEST/libs_linux" --quiet 2>/dev/null || \
pip3 install flask reportlab Pillow python-dateutil \
    --target "$DEST/libs_linux" --quiet

echo "  [2/3] Copie du logiciel..."

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp -r "$SRC/static"    "$DEST/app/"
cp -r "$SRC/templates" "$DEST/app/"
cp    "$SRC/app.py"    "$DEST/app/"

# ── Lanceur Linux ───────────────────────────────
echo "  [3/3] Création des lanceurs..."

cat > "$DEST/LANCER_LINUX.sh" << 'LAUNCHER'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIBS="$SCRIPT_DIR/libs_linux"
cd "$SCRIPT_DIR/app"
export PYTHONPATH="$LIBS"
echo ""
echo "  Démarrage d'Érablière..."
echo "  Le navigateur va s'ouvrir sur http://localhost:5000"
echo "  Ctrl+C pour quitter."
echo ""
python3 app.py
LAUNCHER
chmod +x "$DEST/LANCER_LINUX.sh"

# ── Lanceur Windows (pour quand la clé est sur un PC Windows) ──
cat > "$DEST/LANCER_WINDOWS.bat" << 'WINLAUNCHER'
@echo off
title Erabliere - Demarrage...
color 0A
echo.
echo  Demarrage d'Erabliere...
echo  Le navigateur va s'ouvrir automatiquement.
echo  Ne fermez pas cette fenetre.
echo.
cd /d "%~dp0app"
set PYTHONPATH=%~dp0libs_linux;%~dp0libs
set PYTHONHOME=
if exist "%~dp0python\python.exe" (
    "%~dp0python\python.exe" app.py
) else (
    python app.py
)
pause
WINLAUNCHER

# ── LIRE_MOI ────────────────────────────────────
cat > "$DEST/LIRE_MOI.txt" << 'README'
ÉRABLIÈRE - Logiciel de gestion
================================

LINUX   : ./LANCER_LINUX.sh  (dans un terminal)
WINDOWS : double-clic sur LANCER_WINDOWS.bat

VOS DONNÉES sont dans : data/
→ Sauvegardez ce dossier régulièrement !

Adresse : http://localhost:5000
README

# ── Résumé ──────────────────────────────────────
clear
echo ""
echo "  =========================================="
echo ""
echo "    INSTALLATION TERMINÉE !"
echo ""
echo "  =========================================="
echo ""
echo "  Logiciel installé dans :"
echo "  $DEST"
echo ""
echo "  POUR UTILISER :"
echo ""
echo "  Sur Linux :"
echo "    cd '$DEST'"
echo "    ./LANCER_LINUX.sh"
echo ""
echo "  Sur Windows :"
echo "    Double-clic sur LANCER_WINDOWS.bat"
echo ""
echo "  VOS DONNÉES : $DEST/data/"
echo "  → Sauvegardez ce dossier régulièrement !"
echo ""
echo "  =========================================="
echo ""
