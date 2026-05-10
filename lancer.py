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
ICON_SRC    = os.path.join(APP_DIR, 'static', 'erabliere_icon.png')

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


def create_desktop_shortcut():
    """
    Crée un raccourci .desktop local (~/Bureau ou ~/Desktop) avec
    chemin absolu vers l'icône et le script — contourne les restrictions
    FAT32 qui empêchent KDE/GNOME de faire confiance aux .desktop sur la clé.
    """
    if sys.platform == 'win32':
        return  # Windows : pas besoin, LANCER.vbs suffit

    # Trouver le Bureau
    desktop = None
    for candidate in (
        os.path.join(os.path.expanduser('~'), 'Bureau'),
        os.path.join(os.path.expanduser('~'), 'Desktop'),
    ):
        if os.path.isdir(candidate):
            desktop = candidate
            break
    if desktop is None:
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        os.makedirs(desktop, exist_ok=True)

    shortcut_path = os.path.join(desktop, 'Erabliere.desktop')

    # Installer l'icône dans le thème utilisateur
    icon_dir  = os.path.join(os.path.expanduser('~'), '.local', 'share', 'icons')
    icon_dest = os.path.join(icon_dir, 'erabliere-icon.png')
    icon_path = icon_dest if os.path.exists(icon_dest) else ''

    if os.path.exists(ICON_SRC) and not os.path.exists(icon_dest):
        try:
            import shutil
            os.makedirs(icon_dir, exist_ok=True)
            shutil.copy2(ICON_SRC, icon_dest)
            icon_path = icon_dest
        except Exception:
            pass

    # Trouver python3
    python_exe = sys.executable

    # Écrire le fichier .desktop avec chemins absolus
    content = (
        '[Desktop Entry]\n'
        'Version=1.0\n'
        'Type=Application\n'
        'Name=Érablière\n'
        'GenericName=Logiciel de gestion d’érablière\n'
        'Comment=Clients, factures, stock, production — portable USB\n'
        f'Exec={python_exe} {BASE_DIR}/lancer.py\n'
        f'Icon={icon_path}\n'
        'Terminal=false\n'
        'Categories=Office;Finance;\n'
        'StartupNotify=true\n'
    )

    # Ne recréer que si le contenu a changé (nouvelle clé USB = nouveau chemin)
    existing = ''
    if os.path.exists(shortcut_path):
        try:
            with open(shortcut_path, 'r', encoding='utf-8') as fh:
                existing = fh.read()
        except Exception:
            pass

    if existing == content:
        return  # déjà à jour, rien à faire

    try:
        with open(shortcut_path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        os.chmod(shortcut_path, 0o755)
    except Exception as e:
        return  # silencieux : le raccourci est optionnel

    # Marquer comme approuvé (GNOME + KDE)
    for cmd in (
        ['gio', 'set', shortcut_path, 'metadata::trusted', 'true'],
        ['dbus-send', '--session', '--dest=org.freedesktop.FileManager1',
         '--type=method_call', '/org/freedesktop/FileManager1',
         'org.freedesktop.FileManager1.ShowItems',
         f'array:string:file://{shortcut_path}', 'string:'],
    ):
        try:
            subprocess.run(cmd, capture_output=True, timeout=3)
        except Exception:
            pass

    # Notification tkinter (une seule fois — quand le fichier vient d'être créé)
    if existing == '':
        _notify_shortcut_created(desktop)


def _notify_shortcut_created(desktop):
    """Affiche brièvement un message de bienvenue."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.title("Érablière")
        root.geometry("460x130")
        root.resizable(False, False)
        root.configure(bg='#1b4332')

        root.update_idletasks()
        x = (root.winfo_screenwidth()  - 460) // 2
        y = (root.winfo_screenheight() - 130) // 2
        root.geometry(f"460x130+{x}+{y}")

        tk.Label(root,
            text="\U0001f341  Raccourci Érablière créé sur votre Bureau",
            bg='#1b4332', fg='white',
            font=('Arial', 12, 'bold'), pady=16).pack()

        tk.Label(root,
            text=f"Utilisez l'icône dans  {desktop}\n"
                 "pour lancer le logiciel la prochaine fois.",
            bg='#1b4332', fg='#b7e4c7',
            font=('Arial', 10)).pack()

        # Fermeture automatique après 5 secondes
        root.after(5000, root.destroy)
        root.mainloop()
    except Exception:
        pass


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

        root.update_idletasks()
        x = (root.winfo_screenwidth() - 420) // 2
        y = (root.winfo_screenheight() - 160) // 2
        root.geometry(f"420x160+{x}+{y}")

        tk.Label(root,
            text="\U0001f341  Érablière — Première installation",
            bg='#1b4332', fg='white',
            font=('Arial', 12, 'bold'), pady=14).pack()

        tk.Label(root,
            text="Installation des composants en cours...\n"
                 "Connexion Internet requise (environ 30 secondes)",
            bg='#1b4332', fg='#b7e4c7',
            font=('Arial', 10)).pack()

        tk.Label(root,
            text="Cette étape n'aura lieu qu'une seule fois.",
            bg='#1b4332', fg='#74c69d',
            font=('Arial', 9, 'italic'), pady=8).pack()

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
    # ── Créer le raccourci Bureau (contourne FAT32 / KDE trust) ──────────────
    create_desktop_shortcut()

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

    import importlib.util
    spec = importlib.util.spec_from_file_location('__main__', APP_PY)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = APP_PY
    sys.modules['__main__'] = module
    spec.loader.exec_module(module)


if __name__ == '__main__':
    main()
