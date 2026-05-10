#!/bin/bash
# Lanceur silencieux — Érablière
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PATH="$HOME/.local/bin:$PATH"

# Installer les dépendances si manquantes
if ! python3 -c "import flask, reportlab, PIL" 2>/dev/null; then
    PKGS="flask reportlab Pillow python-dateutil"
    pip3 install $PKGS --break-system-packages --quiet 2>/dev/null || \
    pip3 install $PKGS --user --quiet 2>/dev/null || \
    python3 -m pip install $PKGS --break-system-packages --quiet 2>/dev/null || \
    python3 -m pip install $PKGS --user --quiet 2>/dev/null
fi

# Arrêter une instance déjà en cours
pkill -f "python3 app.py" 2>/dev/null
sleep 0.5

# Démarrer Flask en arrière-plan
python3 app.py &
FLASK_PID=$!

# Attendre que Flask soit prêt (max 15 sec)
for i in $(seq 1 15); do
    sleep 1
    if curl -s http://localhost:5000 >/dev/null 2>&1; then
        break
    fi
done

# Ouvrir le navigateur
xdg-open http://localhost:5000 2>/dev/null || \
firefox http://localhost:5000 2>/dev/null || \
chromium-browser http://localhost:5000 2>/dev/null

wait $FLASK_PID
