"""Delegatum Desktop — lance le serveur local puis ouvre la fenêtre native.

Double-clic sur Delegatum.exe : le backend (uvicorn + FastAPI) démarre sur un
port local libre (127.0.0.1), la fenêtre s'ouvre sur l'application. Les données
vivent dans « data/ », à côté de l'exécutable — sauvegarder = copier ce
dossier, rien ne sort de la machine.

Variables d'environnement :
  DELEGATUM_NO_WINDOW=1  → mode sans fenêtre (serveur seul ; tests, CI)
  DELEGATUM_PORT=<port>  → port fixe (défaut : port libre automatique)
"""

import os
import secrets
import socket
import sys
import threading
import time
from pathlib import Path


def base_dir() -> Path:
    """Dossier de travail : à côté de l'exécutable (bundle) ou racine du dépôt (dev)."""
    if getattr(sys, "frozen", False):  # exécutable PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Ressources embarquées (front compilé) : _MEIPASS si bundle, sinon racine."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return base_dir()


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_server(port: int, tries: int = 200) -> bool:
    for _ in range(tries):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def screen_size() -> tuple:
    """Taille de l'écran (Windows) pour ne pas ouvrir plus grand que lui."""
    try:
        import ctypes

        u = ctypes.windll.user32
        return int(u.GetSystemMetrics(0)), int(u.GetSystemMetrics(1))
    except Exception:
        return 1280, 800


class DesktopApi:
    """API JS → Python exposée à la page (window.pywebview.api.*).

    Les téléchargements <a download> sont silencieusement bloqués dans la
    WebView Windows : les exports de l'application (PDF des PV, statistiques,
    affiches d'élections, CSV des heures, ZIP des notifications, .eml) passent
    donc par « Enregistrer sous » natif — voir frontend/src/lib/download.ts.
    """

    def save_file(self, filename: str, content: str, path=None, b64: bool = False) -> dict:
        import base64 as _base64
        from pathlib import Path as _Path

        if not path:
            import webview

            win = webview.windows[0] if webview.windows else None
            if win is None:
                return {"ok": False, "error": "no-window"}
            chosen = win.create_file_dialog(webview.SAVE_DIALOG, save_filename=filename)
            if not chosen:
                return {"ok": False, "cancelled": True}
            path = chosen[0] if isinstance(chosen, (list, tuple)) else chosen
        data = _base64.b64decode(content) if b64 else str(content).encode("utf-8")
        _Path(str(path)).write_bytes(data)
        return {"ok": True, "path": str(path)}


def _secret_key(data_dir: Path) -> str:
    """Clé de signature JWT propre à l'installation, persistée dans data/.

    Sans elle, chaque démarrage invaliderait les sessions (et la garde de
    sécurité SD_SECRET_KEY refuse les clés d'exemple) — une clé aléatoire de
    64 caractères hex est créée au premier lancement et conservée.
    """
    f = data_dir / ".secret_key"
    if f.exists():
        v = f.read_text(encoding="utf-8").strip()
        if len(v) >= 32:
            return v
    v = secrets.token_hex(32)
    f.write_text(v, encoding="utf-8")
    return v


def main() -> None:
    base = base_dir()
    data = base / "data"
    data.mkdir(exist_ok=True)

    # Premier lancement = pas encore de base → ouvrir directement l'écran de
    # création de la délégation du personnel.
    first_run = not (data / "delegatum.db").exists()

    # Configuration AVANT l'import de l'application (garde SD_SECRET_KEY lue à
    # l'import ; l'URL de base des emails est lue au démarrage du serveur).
    os.environ.setdefault("SD_DATABASE_URL", "sqlite:///" + (data / "delegatum.db").as_posix())
    os.environ.setdefault("SD_EMAIL_DIR", str(data / "emails"))
    os.environ.setdefault("SD_SECRET_KEY", _secret_key(data))
    static = resource_dir() / "static"
    if not getattr(sys, "frozen", False):
        # dev : package backend importable + front compilé du dépôt
        sys.path.insert(0, str(base / "backend"))
        if not static.is_dir():
            static = base / "frontend" / "dist"
    os.environ.setdefault("SD_STATIC_DIR", str(static))

    # Binaire fenêtré (console=False) : stdout/stderr valent None sous Windows,
    # ce qui fait planter la configuration des logs d'uvicorn (isatty sur None).
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    import uvicorn
    from app.main import app

    port = int(os.environ.get("DELEGATUM_PORT") or 0) or free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    os.environ.setdefault("SD_BASE_URL", url)
    wait_server(port)
    ui_url = url + ("create" if first_run else "")

    if os.environ.get("DELEGATUM_NO_WINDOW") == "1":
        # mode headless (tests/CI) : stdout peut être absent (binaire windowed)
        try:
            print(url, flush=True)
        except Exception:
            pass
        try:
            (base / "url.txt").write_text(url + "\n", encoding="utf-8")
        except Exception:
            pass
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        return

    try:
        import webview  # fenêtre native (WebView2 sous Windows)

        sw, sh = screen_size()
        w = min(1320, max(900, sw - 80))
        h = min(880, max(600, sh - 120))
        webview.create_window(
            "Delegatum",
            ui_url,
            width=w,
            height=h,
            min_size=(760, 540),
            js_api=DesktopApi(),
        )
        webview.start()  # bloque jusqu'à la fermeture de la fenêtre
        return
    except Exception:  # fenêtre indisponible → navigateur par défaut
        import webbrowser

        webbrowser.open(ui_url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:  # binaire fenêtré : consigner le crash dans error.log
        import traceback
        try:
            (base_dir() / "error.log").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
        except Exception:
            pass
        raise
