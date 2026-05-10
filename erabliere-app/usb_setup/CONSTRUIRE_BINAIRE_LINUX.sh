#!/bin/bash
# ══════════════════════════════════════════════════════
#  Construction d'un binaire Linux autonome (PyInstaller)
# ══════════════════════════════════════════════════════

set -e
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  CONSTRUCTION BINAIRE LINUX AUTONOME            ║"
echo "║  Aucune installation requise sur l'ordi cible   ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")/.."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERREUR: python3 requis pour compiler.${NC}"
    exit 1
fi

echo -e "${GREEN}Installation de PyInstaller...${NC}"
pip3 install pyinstaller --quiet

echo -e "${GREEN}Installation des dépendances...${NC}"
pip3 install flask reportlab Pillow python-dateutil --quiet

echo ""
echo -e "${GREEN}Construction en cours (3-5 minutes)...${NC}"
echo ""

pyinstaller --noconfirm --onedir \
    --name "Erabliere" \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --hidden-import "reportlab.graphics" \
    --hidden-import "reportlab.pdfgen" \
    --hidden-import "PIL._imaging" \
    --collect-all "flask" \
    --collect-all "jinja2" \
    --collect-all "werkzeug" \
    app.py

if [ ! -f "dist/Erabliere/Erabliere" ]; then
    echo -e "${RED}ERREUR lors de la construction.${NC}"
    exit 1
fi

mkdir -p "dist/Erabliere/data/pdfs"

# Créer le lanceur shell
cat > "dist/Erabliere/LANCER.sh" << 'LAUNCHER'
#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
echo "Démarrage d'Érablière..."
./Erabliere
LAUNCHER
chmod +x "dist/Erabliere/LANCER.sh"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  COMPILATION RÉUSSIE !                          ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  Dossier : dist/Erabliere/                       ║"
echo "║                                                  ║"
echo "║  Copiez ce dossier sur votre clé USB.            ║"
echo "║  Lancez avec : ./LANCER.sh                       ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
