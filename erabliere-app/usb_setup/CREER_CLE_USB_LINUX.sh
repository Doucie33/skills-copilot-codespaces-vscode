#!/bin/bash
# ══════════════════════════════════════════════════════
#  Création de la clé USB portable — Érablière (Linux)
# ══════════════════════════════════════════════════════

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║    CRÉATION DE LA CLÉ USB PORTABLE              ║"
echo "║    Logiciel de gestion d'Érablière              ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Vérifier qu'on est dans le bon dossier ──────────────────────────────────
if [ ! -f "../app.py" ]; then
    echo -e "${RED}ERREUR: Lancez ce script depuis le dossier usb_setup/${NC}"
    exit 1
fi

# ── Trouver la clé USB ──────────────────────────────────────────────────────
echo "Périphériques de stockage détectés :"
echo ""
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E "disk|part|sd|usb" 2>/dev/null || \
    df -h | grep -v tmpfs | grep -v udev
echo ""

echo -n "Entrez le point de montage de votre clé USB (ex: /media/user/MACLÉ) : "
read USB_MOUNT

if [ ! -d "$USB_MOUNT" ]; then
    echo -e "${RED}ERREUR: Le dossier $USB_MOUNT n'existe pas.${NC}"
    echo "Astuce: Insérez la clé USB et vérifiez avec: ls /media/$USER/"
    exit 1
fi

APP_DIR="$USB_MOUNT/Erabliere"
echo ""
echo "Cible : $APP_DIR"
echo ""
echo -n "Confirmer la création? (o/n) : "
read CONFIRM
if [ "$CONFIRM" != "o" ] && [ "$CONFIRM" != "O" ]; then
    exit 0
fi

# ── Créer la structure ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}[1/4] Création de la structure de dossiers...${NC}"
mkdir -p "$APP_DIR/app/static"
mkdir -p "$APP_DIR/app/templates"
mkdir -p "$APP_DIR/data/pdfs"
mkdir -p "$APP_DIR/venv"

# ── Créer l'environnement virtuel portable ──────────────────────────────────
echo -e "${GREEN}[2/4] Création de l'environnement Python portable...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERREUR: python3 n'est pas installé.${NC}"
    echo "Installez-le: sudo apt install python3 python3-venv"
    exit 1
fi

python3 -m venv "$APP_DIR/venv"

# ── Installer les dépendances dans le venv ──────────────────────────────────
echo -e "${GREEN}[3/4] Installation des dépendances...${NC}"
echo "     (Flask, ReportLab, Pillow — quelques minutes)"

"$APP_DIR/venv/bin/pip" install flask reportlab Pillow python-dateutil \
    --quiet --no-warn-script-location

# ── Copier l'application ────────────────────────────────────────────────────
echo -e "${GREEN}[4/4] Copie de l'application...${NC}"
cp -r ../static    "$APP_DIR/app/"
cp -r ../templates "$APP_DIR/app/"
cp    ../app.py    "$APP_DIR/app/"

# ── Créer les lanceurs ──────────────────────────────────────────────────────
echo "Création des scripts de lancement..."

# Lanceur principal (chemin auto-détecté depuis la clé)
cat > "$APP_DIR/LANCER_ERABLIERE.sh" << 'LAUNCHER'
#!/bin/bash
# Lanceur portable Érablière
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/app"
echo "Démarrage d'Érablière..."
echo "Navigateur : http://localhost:5000"
echo "Ctrl+C pour quitter."
"$SCRIPT_DIR/venv/bin/python3" app.py
LAUNCHER

chmod +x "$APP_DIR/LANCER_ERABLIERE.sh"

# Lanceur silencieux (background)
cat > "$APP_DIR/LANCER_SILENCIEUX.sh" << 'SILENT'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/app"
"$SCRIPT_DIR/venv/bin/python3" app.py &
SILENT

chmod +x "$APP_DIR/LANCER_SILENCIEUX.sh"

# Fichier .desktop pour double-clic depuis le gestionnaire de fichiers
cat > "$APP_DIR/Erabliere.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Érablière - Gestion
Comment=Logiciel de gestion d'érablière
Exec=bash -c 'cd "$(dirname %k)/app" && "$(dirname %k)/venv/bin/python3" app.py'
Icon=applications-office
Terminal=true
Categories=Office;Finance;
DESKTOP
chmod +x "$APP_DIR/Erabliere.desktop"

# README
cat > "$APP_DIR/LIRE_MOI.txt" << 'README'
ÉRABLIÈRE — Logiciel de gestion portable (Linux)
=================================================

UTILISATION :
  Ouvrir un terminal dans ce dossier, puis :
    ./LANCER_ERABLIERE.sh

  Ou double-cliquer sur Erabliere.desktop
  (activer "Autoriser l'exécution" si demandé)

VOS DONNÉES :
  Dossier : data/
  Base de données : data/erabliere.db
  → Sauvegardez ce dossier régulièrement !

COMPATIBLE : Ubuntu, Kubuntu, Debian et dérivés
README

# ── Résumé ──────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  INSTALLATION TERMINÉE AVEC SUCCÈS !            ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  Emplacement : $APP_DIR"
echo "║                                                  ║"
echo "║  Pour lancer :                                   ║"
echo "║    ./LANCER_ERABLIERE.sh                         ║"
echo "║                                                  ║"
echo "║  Données dans : data/                            ║"
echo "║  → Sauvegardez ce dossier !                      ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
