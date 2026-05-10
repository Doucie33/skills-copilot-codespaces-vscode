#!/bin/bash
# ════════════════════════════════════════════════════════
#  ÉRABLIÈRE — Lanceur Linux (secours / terminal)
#  Utilisez de préférence LANCER.desktop (double-clic dans
#  le gestionnaire de fichiers) pour lancer sans terminal.
#  Ce script sert de secours ou pour les serveurs sans GUI.
# ════════════════════════════════════════════════════════
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Trouver Python 3
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
        [ "$VER" = "3" ] && PYTHON="$cmd" && break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Python 3 est requis. Installez-le avec :"
    echo "  sudo apt install python3"
    read -p "Appuyez sur Entrée..."
    exit 1
fi

"$PYTHON" "$SCRIPT_DIR/lancer.py"
