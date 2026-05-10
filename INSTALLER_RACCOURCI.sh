#!/bin/bash
# ══════════════════════════════════════════════════════
#  ÉRABLIÈRE — Installe l'icône sur le bureau (une fois)
#  Lancez ce script UNE SEULE FOIS.
#  Ensuite : double-cliquez sur l'icône du bureau.
# ══════════════════════════════════════════════════════
clear

VERT='\033[0;32m'
ROUGE='\033[0;31m'
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
ICON_FILE="$APP_DIR/static/erabliere_icon.png"

# ── Trouver le vrai dossier Bureau (fr/en) ────────────────────────────────
BUREAU=""
for candidate in "$HOME/Bureau" "$HOME/Desktop" "$HOME/Рабочий стол"; do
    if [ -d "$candidate" ]; then
        BUREAU="$candidate"
        break
    fi
done
# Si aucun trouvé, utiliser xdg-user-dir
if [ -z "$BUREAU" ]; then
    BUREAU="$(xdg-user-dir DESKTOP 2>/dev/null)"
fi
# Créer le dossier si inexistant
if [ -z "$BUREAU" ] || [ ! -d "$BUREAU" ]; then
    BUREAU="$HOME/Bureau"
    mkdir -p "$BUREAU"
fi

DESKTOP_FILE="$BUREAU/Erabliere.desktop"
echo "  Bureau détecté : $BUREAU"

# ── Créer l'icône PNG ─────────────────────────────────────────────────────
echo "  Création de l'icône..."
python3 - "$APP_DIR" << 'PYEOF'
import sys, os, math
try:
    from PIL import Image, ImageDraw
    app_dir = sys.argv[1]
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([8, 8, size-8, size-8], radius=40, fill=(45, 106, 79, 255))
    cx, cy = size//2, size//2 - 10
    r_out, r_in = 90, 38
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill=(255, 255, 255, 230))
    draw.rounded_rectangle([cx-8, cy+50, cx+8, cy+90], radius=4, fill=(255, 255, 255, 200))
    icon_path = os.path.join(app_dir, 'static', 'erabliere_icon.png')
    img.save(icon_path)
    print(f"  ✓ Icône créée")
except Exception as e:
    print(f"  (icône générique utilisée)")
PYEOF

# ── Rendre le lanceur exécutable ──────────────────────────────────────────
chmod +x "$LAUNCHER"

# ── Installer Flask correctement ──────────────────────────────────────────
echo ""
echo "  Vérification des composants Python..."

install_deps() {
    PKGS="flask reportlab Pillow python-dateutil"
    # Essai 1 : pip3 --break-system-packages (Ubuntu 23+)
    pip3 install $PKGS --break-system-packages --quiet 2>/dev/null && return 0
    # Essai 2 : pip3 --user
    pip3 install $PKGS --user --quiet 2>/dev/null && return 0
    # Essai 3 : python3 -m pip --break-system-packages
    python3 -m pip install $PKGS --break-system-packages --quiet 2>/dev/null && return 0
    # Essai 4 : python3 -m pip --user
    python3 -m pip install $PKGS --user --quiet 2>/dev/null && return 0
    # Essai 5 : apt pour flask + pip pour reportlab
    sudo apt-get install -y python3-flask python3-pil python3-dateutil 2>/dev/null
    pip3 install reportlab --break-system-packages --quiet 2>/dev/null || \
    pip3 install reportlab --user --quiet 2>/dev/null
    return 0
}

if python3 -c "import flask, reportlab, PIL, dateutil" 2>/dev/null; then
    echo "  ✓ Tous les composants déjà installés"
else
    echo "  Installation des composants (1-2 min)..."
    # S'assurer que pip est disponible
    if ! command -v pip3 &>/dev/null; then
        sudo apt-get install -y python3-pip 2>/dev/null
    fi
    install_deps
fi

# Vérification finale
if python3 -c "import flask" 2>/dev/null; then
    echo "  ✓ Flask opérationnel"
else
    echo -e "  ${ROUGE}⚠ Flask non trouvé — le logiciel pourrait ne pas démarrer${NC}"
fi

# ── Mettre à jour lancer.sh pour utiliser --user si nécessaire ────────────
# (ajout de ~/.local/bin au PATH pour les modules --user)
cat > "$LAUNCHER" << LAUNCHER_EOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$SCRIPT_DIR"
export PATH="\$HOME/.local/bin:\$PATH"
export PYTHONPATH="\$HOME/.local/lib/python3\$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')/site-packages:\$PYTHONPATH"

if ! python3 -c "import flask" 2>/dev/null; then
    pip3 install flask reportlab Pillow python-dateutil --user --quiet 2>/dev/null
fi

pkill -f "python3 app.py" 2>/dev/null
sleep 0.5

python3 app.py &
FLASK_PID=\$!

for i in \$(seq 1 15); do
    sleep 1
    if curl -s http://localhost:5000 >/dev/null 2>&1; then
        break
    fi
done

xdg-open http://localhost:5000 2>/dev/null || \
firefox http://localhost:5000 2>/dev/null || \
chromium-browser http://localhost:5000 2>/dev/null

wait \$FLASK_PID
LAUNCHER_EOF
chmod +x "$LAUNCHER"

# ── Créer le fichier .desktop ──────────────────────────────────────────────
echo ""
echo "  Création du raccourci sur le bureau : $DESKTOP_FILE"

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
EOF

chmod +x "$DESKTOP_FILE"

# Marquer comme approuvé KDE/Gnome
gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
kwriteconfig5 --file "$DESKTOP_FILE" --group "Desktop Entry" --key X-KDE-SubstituteVariables false 2>/dev/null || true

# ── Résultat ──────────────────────────────────────────────────────────────
echo ""
echo -e "${VERT}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${VERT}  ║   ✓ RACCOURCI INSTALLÉ SUR LE BUREAU !      ║${NC}"
echo -e "${VERT}  ╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GRAS}Pour lancer le logiciel :${NC}"
echo "    → Double-cliquez sur l'icône « Érablière » sur votre bureau"
echo ""
echo "  Si KDE demande « Exécuter ou Afficher », choisissez : Exécuter"
echo "  Si l'icône n'apparaît pas, appuyez sur F5 sur le bureau."
echo ""

xdg-open "$BUREAU" 2>/dev/null &
sleep 1

read -p "  Lancer le logiciel maintenant ? (o/n) : " LANCER
if [[ "$LANCER" == "o" || "$LANCER" == "O" ]]; then
    bash "$LAUNCHER"
fi
