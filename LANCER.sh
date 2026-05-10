#!/bin/bash
# ══════════════════════════════════════════════════════════
#  ÉRABLIÈRE — Lanceur Linux
#  Double-cliquez sur ce fichier dans votre gestionnaire
#  de fichiers, OU tapez :  bash LANCER.sh
# ══════════════════════════════════════════════════════════

# Se placer dans le dossier du script (important pour clé USB)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERT='\033[0;32m'
JAUNE='\033[1;33m'
ROUGE='\033[0;31m'
NC='\033[0m'
GRAS='\033[1m'

clear
echo ""
echo -e "${VERT}  ╔════════════════════════════════════════════════╗${NC}"
echo -e "${VERT}  ║     ÉRABLIÈRE — Logiciel de gestion           ║${NC}"
echo -e "${VERT}  ╚════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Étape 1 : Vérifier Python 3 ─────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
        if [ "$VER" = "3" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "  ${ROUGE}[!] Python 3 n'est pas installé.${NC}"
    echo ""
    echo "  Installation automatique en cours..."

    # Essayer apt (Ubuntu/Debian/Linux Mint)
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y python3 python3-pip 2>/dev/null
    # Essayer dnf (Fedora/RHEL)
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-pip 2>/dev/null
    # Essayer pacman (Arch)
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python python-pip 2>/dev/null
    else
        echo -e "  ${ROUGE}Impossible d'installer Python automatiquement.${NC}"
        echo ""
        echo "  Installez Python 3 manuellement :"
        echo "    sudo apt install python3 python3-pip"
        echo ""
        read -p "  Appuyez sur Entrée pour fermer..."
        exit 1
    fi

    PYTHON="python3"
fi

echo -e "  ${VERT}[✓]${NC} Python détecté : $($PYTHON --version)"

# ─── Étape 2 : Vérifier / installer pip ──────────────────────────────────────
if ! $PYTHON -m pip --version &>/dev/null; then
    echo "  [~] Installation de pip..."
    $PYTHON -m ensurepip --upgrade 2>/dev/null || \
    curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON 2>/dev/null || \
    sudo apt-get install -y python3-pip 2>/dev/null
fi

# ─── Étape 2b : Installer l'icône sur le Bureau (première fois) ──────────────
ICON_SRC="$SCRIPT_DIR/erabliere-app/static/erabliere_icon.png"
ICON_DEST="$HOME/.local/share/icons/erabliere-icon.png"
DESKTOP_DEST="$HOME/.local/share/applications/erabliere.desktop"

if [ ! -f "$DESKTOP_DEST" ] && [ -f "$ICON_SRC" ]; then
    mkdir -p "$HOME/.local/share/icons"
    mkdir -p "$HOME/.local/share/applications"
    cp "$ICON_SRC" "$ICON_DEST" 2>/dev/null
    cat > "$DESKTOP_DEST" << DESKTOPEOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Érablière
Comment=Logiciel de gestion d'érablière
Exec=bash -c 'bash "$SCRIPT_DIR/LANCER.sh"'
Icon=$ICON_DEST
Terminal=true
Categories=Office;Finance;
DESKTOPEOF
    chmod +x "$DESKTOP_DEST" 2>/dev/null
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null
    echo -e "  ${VERT}[✓]${NC} Icône installée dans le menu des applications."
fi

# ─── Étape 3 : Installer les dépendances (une seule fois) ────────────────────
if [ ! -f "erabliere-app/.deps_ok" ]; then
    echo ""
    echo -e "  ${JAUNE}[~] Installation des composants (première fois uniquement)...${NC}"
    echo "      Patientez quelques secondes..."
    echo ""

    $PYTHON -m pip install flask reportlab Pillow --quiet --user 2>/dev/null || \
    $PYTHON -m pip install flask reportlab Pillow --quiet --break-system-packages 2>/dev/null

    if $PYTHON -c "import flask" &>/dev/null; then
        touch "erabliere-app/.deps_ok"
        echo -e "  ${VERT}[✓]${NC} Composants installés."
    else
        echo -e "  ${ROUGE}[!] Erreur lors de l'installation.${NC}"
        echo "  Vérifiez votre connexion Internet et réessayez."
        read -p "  Appuyez sur Entrée pour fermer..."
        exit 1
    fi
else
    echo -e "  ${VERT}[✓]${NC} Composants prêts."
fi

# ─── Étape 4 : Créer les dossiers data si absents ────────────────────────────
mkdir -p erabliere-app/data/pdfs

# ─── Étape 5 : Ouvrir le navigateur après 2 secondes ─────────────────────────
(
    sleep 2
    # Essayer les différents lanceurs de navigateur selon la distribution
    for browser in xdg-open gnome-open kde-open firefox chromium-browser google-chrome; do
        if command -v "$browser" &>/dev/null; then
            "$browser" http://localhost:5000 &>/dev/null &
            break
        fi
    done
) &

# ─── Étape 6 : Lancer l'application ──────────────────────────────────────────
echo ""
echo -e "${VERT}  ╔════════════════════════════════════════════════╗${NC}"
echo -e "${VERT}  ║   Logiciel démarré !                          ║${NC}"
echo -e "${VERT}  ║   Adresse : http://localhost:5000             ║${NC}"
echo -e "${VERT}  ║                                               ║${NC}"
echo -e "${VERT}  ║   Appuyez sur Ctrl+C pour arrêter.           ║${NC}"
echo -e "${VERT}  ╚════════════════════════════════════════════════╝${NC}"
echo ""

cd erabliere-app
ERABLIERE_NO_BROWSER=1 $PYTHON app.py

echo ""
echo "  Application arrêtée."
read -p "  Appuyez sur Entrée pour fermer..."
