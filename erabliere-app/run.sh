#!/bin/bash
echo "========================================"
echo "  ERABLIERE - Logiciel de gestion"
echo "========================================"
echo ""

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo "ERREUR: Python3 n'est pas installé."
    echo "Installez-le avec: sudo apt install python3 python3-pip"
    exit 1
fi

# Install dependencies
echo "Installation des dépendances..."
pip3 install flask reportlab Pillow python-dateutil --quiet

echo ""
echo "Démarrage du serveur..."
echo "Ouvrez votre navigateur à l'adresse: http://localhost:5000"
echo "Appuyez sur Ctrl+C pour arrêter."
echo ""

# Try to open browser
(sleep 2 && (xdg-open http://localhost:5000 2>/dev/null || open http://localhost:5000 2>/dev/null || true)) &

python3 app.py
