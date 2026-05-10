#!/bin/bash
# ══════════════════════════════════════════════════════
#  ÉRABLIÈRE — Installe l'icône sur le bureau (une fois)
#  Lancez ce script UNE SEULE FOIS.
#  Ensuite : double-cliquez sur l'icône du bureau.
# ══════════════════════════════════════════════════════
clear

VERT='\033[0;32m'
GRAS='\033[1m'
NC='\033[0m'

echo ""
echo -e "${VERT}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${VERT}  ║   ÉRABLIÈRE — Création du raccourci bureau  ║${NC}"
echo -e "${VERT}  ╚══════════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/erabliere-app"
LAUNCHER="$APP_DIR/lancer.sh"
DESKTOP_FILE="$HOME/Desktop/Erabliere.desktop"
ICON_FILE="$APP_DIR/static/erabliere_icon.png"

# ── Créer l'icône PNG (feuille d'érable verte) ────────────────────────────
echo "  Création de l'icône..."
python3 - << 'PYEOF'
import os, sys
try:
    from PIL import Image, ImageDraw, ImageFont
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Fond vert arrondi
    draw.rounded_rectangle([8, 8, size-8, size-8], radius=40,
                            fill=(45, 106, 79, 255))
    # Feuille d'érable simplifiée (étoile à 5 branches)
    import math
    cx, cy = size//2, size//2 - 10
    r_out, r_in = 90, 38
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill=(255, 255, 255, 230))
    # Tige
    draw.rounded_rectangle([cx-8, cy+50, cx+8, cy+90], radius=4,
                            fill=(255, 255, 255, 200))
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'erabliere-app', 'static', 'erabliere_icon.png')
    img.save(icon_path)
    print(f"  ✓ Icône créée : {icon_path}")
except Exception as e:
    print(f"  (icône par défaut sera utilisée : {e})")
PYEOF

# ── Rendre le lanceur exécutable ──────────────────────────────────────────
chmod +x "$LAUNCHER"

# ── Installer les dépendances Python ──────────────────────────────────────
echo ""
echo "  Vérification des composants Python..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "  Installation de Flask (1-2 min)..."
    pip3 install flask reportlab Pillow python-dateutil --quiet 2>/dev/null || \
    python3 -m pip install flask reportlab Pillow python-dateutil --quiet 2>/dev/null
    echo "  ✓ Composants installés"
else
    echo "  ✓ Composants déjà installés"
fi

# ── Créer le fichier .desktop ──────────────────────────────────────────────
echo ""
echo "  Création du raccourci sur le bureau..."

# Choisir l'icône (personnalisée ou système)
if [ -f "$ICON_FILE" ]; then
    ICON_ENTRY="$ICON_FILE"
else
    ICON_ENTRY="applications-office"
fi

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Érablière
GenericName=Gestion d'érablière
Comment=Logiciel de gestion d'érablière
Exec=bash "$LAUNCHER"
Icon=$ICON_ENTRY
Terminal=false
StartupNotify=true
Categories=Office;Finance;
Keywords=erabliere;facture;client;comptabilite;
EOF

chmod +x "$DESKTOP_FILE"

# Marquer comme approuvé (Kubuntu/KDE)
gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true

# ── Créer aussi un lanceur dans /usr/local/bin (optionnel) ────────────────
# Pour lancer depuis n'importe où avec "erabliere"
if [ -w "/usr/local/bin" ] || sudo -n true 2>/dev/null; then
    sudo ln -sf "$LAUNCHER" /usr/local/bin/erabliere 2>/dev/null || true
fi

# ── Résultat ──────────────────────────────────────────────────────────────
echo ""
echo -e "${VERT}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${VERT}  ║   ✓ RACCOURCI INSTALLÉ SUR LE BUREAU !      ║${NC}"
echo -e "${VERT}  ╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GRAS}Pour lancer le logiciel :${NC}"
echo "    → Double-cliquez sur l'icône « Érablière » sur votre bureau"
echo ""
echo "  Si l'icône n'apparaît pas de suite, appuyez sur F5 sur le bureau."
echo ""

# Ouvrir le bureau dans Dolphin pour montrer l'icône
xdg-open "$HOME/Desktop" 2>/dev/null &
sleep 1

# Proposer de lancer maintenant
read -p "  Lancer le logiciel maintenant ? (o/n) : " LANCER
if [[ "$LANCER" == "o" || "$LANCER" == "O" ]]; then
    bash "$LAUNCHER"
fi
