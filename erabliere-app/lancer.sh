#!/bin/bash
# Lanceur silencieux — Érablière
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Installer les dépendances si manquantes
if ! python3 -c "import flask" 2>/dev/null; then
    if command -v zenity &>/dev/null; then
        zenity --info --title="Érablière" \
               --text="Première utilisation — Installation automatique (1-2 min).\nVeuillez patienter..." \
               --timeout=3 2>/dev/null &
    fi
    pip3 install flask reportlab Pillow python-dateutil --quiet 2>/dev/null || \
    python3 -m pip install flask reportlab Pillow python-dateutil --quiet 2>/dev/null
fi

# Arrêter une instance déjà en cours
pkill -f "python3 app.py" 2>/dev/null
sleep 0.5

# Démarrer Flask en arrière-plan
python3 app.py &
FLASK_PID=$!

# Attendre que Flask soit prêt
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
