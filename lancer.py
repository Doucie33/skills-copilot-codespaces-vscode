#!/usr/bin/env python3
"""
Lanceur portable Érablière — Windows et Linux
Double-cliquez sur LANCER.vbs (Windows) ou LANCER.desktop (Linux)
"""
import os
import sys
import subprocess
import threading
import webbrowser
import time

# ── Chemins portables (relatifs à ce fichier, donc sur la clé USB) ────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
APP_DIR     = os.path.join(BASE_DIR, 'erabliere-app')
APP_PY      = os.path.join(APP_DIR, 'app.py')
DATA_DIR    = os.path.join(BASE_DIR, 'data')
DEPS_FLAG   = os.path.join(APP_DIR, '.deps_ok')

# Indiquer à app.py où stocker les données (sur la clé USB, pas dans l'app)
os.environ['ERABLIERE_DATA_DIR'] = DATA_DIR
os.environ['ERABLIERE_NO_BROWSER'] = '1'

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'pdfs'), exist_ok=True)


def show_error(message):
    """Affiche une boîte d'erreur graphique."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Érablière", message)
        root.destroy()
    except Exception:
        print("ERREUR:", message)


def install_deps():
    """
    Installe Flask et ReportLab la première fois.
    Affiche une fenêtre de progression via tkinter.
    """
    if os.path.exists(DEPS_FLAG):
        return True

    # Vérifier si flask est déjà disponible (installé globalement)
    try:
        import flask  # noqa
        open(DEPS_FLAG, 'w').write('ok')
        return True
    except ImportError:
        pass

    # Afficher une fenêtre de progression
    success = [False]
    error_msg = ['']

    try:
        import tkinter as tk

        root = tk.Tk()
        root.title("Érablière")
        root.geometry("420x160")
        root.resizable(False, False)
        root.configure(bg='#1b4332')

        # Centrer la fenêtre
        root.update_idletasks()
        x = (root.winfo_screenwidth() - 420) // 2
        y = (root.winfo_screenheight() - 160) // 2
        root.geometry(f"420x160+{x}+{y}")

        lbl_titre = tk.Label(root,
            text="🍁  Érablière — Première installation",
            bg='#1b4332', fg='white',
            font=('Arial', 12, 'bold'), pady=14)
        lbl_titre.pack()

        lbl_status = tk.Label(root,
            text="Installation des composants en cours...\n"
                 "Connexion Internet requise (environ 30 secondes)",
            bg='#1b4332', fg='#b7e4c7',
            font=('Arial', 10))
        lbl_status.pack()

        lbl_note = tk.Label(root,
            text="Cette étape n'aura lieu qu'une seule fois.",
            bg='#1b4332', fg='#74c69d',
            font=('Arial', 9, 'italic'), pady=8)
        lbl_note.pack()

        def do_install():
            try:
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install',
                     'flask', 'reportlab', 'Pillow',
                     '--quiet', '--user'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError:
                # Essai avec --break-system-packages (Ubuntu 23+)
                try:
                    subprocess.check_call(
                        [sys.executable, '-m', 'pip', 'install',
                         'flask', 'reportlab', 'Pillow',
                         '--quiet', '--break-system-packages'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except subprocess.CalledProcessError as e:
                    error_msg[0] = str(e)
                    root.after(0, root.destroy)
                    return

            open(DEPS_FLAG, 'w').write('ok')
            success[0] = True
            root.after(0, root.destroy)

        threading.Thread(target=do_install, daemon=True).start()
        root.mainloop()

    except ImportError:
        # tkinter absent : installation silencieuse
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install',
                 'flask', 'reportlab', 'Pillow', '--quiet', '--user'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            open(DEPS_FLAG, 'w').write('ok')
            success[0] = True
        except subprocess.CalledProcessError as e:
            error_msg[0] = str(e)

    if not success[0]:
        show_error(
            "Impossible d'installer les composants requis.\n\n"
            "Vérifiez votre connexion Internet\n"
            "et relancez le logiciel.\n\n"
            f"Détail : {error_msg[0]}"
        )
        return False

    return True


def main():
    # ── Vérifier que app.py est présent ──────────────────────────────────────
    if not os.path.exists(APP_PY):
        show_error(
            "Fichier manquant : erabliere-app/app.py\n\n"
            "Assurez-vous que le dossier erabliere-app\n"
            "est présent à côté de ce fichier."
        )
        sys.exit(1)

    # ── Installer les dépendances si nécessaire ───────────────────────────────
    if not install_deps():
        sys.exit(1)

    # ── Vérifier que flask est importable ────────────────────────────────────
    try:
        # Ajouter le dossier utilisateur pip au path si nécessaire
        import site
        user_site = site.getusersitepackages()
        if user_site not in sys.path:
            sys.path.insert(0, user_site)
        import flask  # noqa
    except ImportError:
        show_error(
            "Flask n'est pas disponible.\n\n"
            "Supprimez le fichier erabliere-app/.deps_ok\n"
            "et relancez le logiciel pour réinstaller."
        )
        sys.exit(1)

    # ── Ouvrir le navigateur après 2,5 secondes ───────────────────────────────
    def open_browser():
        time.sleep(2.5)
        webbrowser.open('http://localhost:5000')

    threading.Thread(target=open_browser, daemon=True).start()

    # ── Lancer Flask ──────────────────────────────────────────────────────────
    os.chdir(APP_DIR)
    sys.path.insert(0, APP_DIR)

    # Exécuter app.py comme module principal
    import importlib.util
    spec = importlib.util.spec_from_file_location('__main__', APP_PY)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = APP_PY
    sys.modules['__main__'] = module
    spec.loader.exec_module(module)


if __name__ == '__main__':
    main()
