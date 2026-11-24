# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Connecte un serveur MCP de la passerelle LiteLLM Liora à Claude Code.

Fonctionne sur macOS, Windows et Linux. Lancement :

    uv run scripts/setup.py                  configure le serveur par défaut (liora-db)
    uv run scripts/setup.py --name test-db   configure sous un autre nom (tests)
    uv run scripts/setup.py --check          vérifie l'installation, ne change rien

Les saisies passent par des fenêtres (tkinter). La clé n'est jamais affichée : elle va
directement de la fenêtre de saisie à la config de Claude Code (portée « user »).
Aucune valeur interne n'est dans ce repo : elles sont dans le fichier de config local
(~/.config/liora-mcp/config.json), rempli au premier lancement.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

CONFIG_FILE = Path(os.environ.get("LIORA_MCP_CONFIG", Path.home() / ".config" / "liora-mcp" / "config.json"))
TITLE = "Liora MCP setup"


def say(msg: str) -> None:
    print(msg, flush=True)


def step(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"\n✖ {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


# ── Fenêtres de saisie ────────────────────────────────────────────────────────
def _point_tk_to_its_files() -> None:
    """Le Python fourni par uv ne retrouve pas Tcl/Tk depuis l'environnement isolé de `uv run`
    (« Can't find a usable init.tcl »). On lui indique où sont les fichiers, sous l'installation
    de base : lib/tcl8.x (macOS, Linux) ou tcl/tcl8.x (Windows)."""
    base = Path(sys.base_prefix)
    for var, pattern, marker in (("TCL_LIBRARY", "tcl8*", "init.tcl"), ("TK_LIBRARY", "tk8*", "tk.tcl")):
        if os.environ.get(var):
            continue
        for parent in (base / "lib", base / "tcl"):
            found = [p for p in sorted(parent.glob(pattern)) if (p / marker).exists()]
            if found:
                os.environ[var] = str(found[-1])
                break


def ask(prompt: str, default: str = "", hidden: bool = False) -> str:
    """Pose une question dans une fenêtre. Repli sur le terminal s'il n'y a pas d'écran."""
    try:
        _point_tk_to_its_files()
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)  # au premier plan, devant Claude Code
        value = simpledialog.askstring(
            TITLE, prompt, initialvalue=default, show="*" if hidden else None, parent=root
        )
        root.destroy()
    except Exception as exc:  # pas d'écran, ou Tk indisponible
        print(f"(fenêtre indisponible : {type(exc).__name__}: {exc})", file=sys.stderr, flush=True)
        if not sys.stdin.isatty():
            fail("Impossible d'ouvrir une fenêtre de saisie sur ce poste (pas d'affichage). "
                 "Lance le setup dans un terminal : uv run scripts/setup.py")
        import getpass

        value = getpass.getpass(prompt + " ") if hidden else (input(f"{prompt} [{default}] ") or default)
    if value is None:
        fail("Saisie annulée.")
    return value.strip()


# ── HTTP ──────────────────────────────────────────────────────────────────────
def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, ""


# ── Claude Code ───────────────────────────────────────────────────────────────
def claude_bin() -> str:
    path = shutil.which("claude")
    if not path:
        fail("La commande « claude » est introuvable. Installe Claude Code "
             "(https://claude.com/claude-code), puis relance le setup.")
    return path


def claude(*args: str, quiet: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run([claude_bin(), *args], capture_output=quiet, text=True)


def show_server(name: str) -> bool:
    res = subprocess.run([claude_bin(), "mcp", "get", name], capture_output=True, text=True)
    out = "\n".join(l for l in (res.stdout + res.stderr).splitlines() if "x-litellm-api-key" not in l.lower())
    say(out.strip())
    return res.returncode == 0


# ── Config ────────────────────────────────────────────────────────────────────
def load_or_create_config(check_only: bool) -> dict:
    step("Configuration de la passerelle")
    if CONFIG_FILE.exists():
        say(f"Configuration trouvée : {CONFIG_FILE}")
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if check_only:
        fail(f"Pas de configuration ({CONFIG_FILE}). Lance le setup sans --check.")
    say("Premier lancement : deux valeurs à recopier depuis la page interne « Liora MCP ».")
    gateway = ask("Adresse de la passerelle (ex. https://ai-gateway.exemple.tech) :", "https://")
    server = ask("Nom du serveur MCP sur la passerelle (champ « serveur ») :")
    if not gateway.startswith("https://"):
        fail("L'adresse doit commencer par https://")
    if not server:
        fail("Nom de serveur vide.")
    cfg = {
        "gateway_url": gateway.rstrip("/"),
        "servers": [{"name": "liora-db", "gateway_server": server,
                     "description": "Entrepôt de données Nexus (lecture seule)"}],
    }
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass
    say(f"Configuration enregistrée dans {CONFIG_FILE}")
    return cfg


# ── Setup ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Connecte un MCP de la passerelle Liora à Claude Code.")
    parser.add_argument("--name", help="nom du serveur dans Claude Code (défaut : celui de la config)")
    parser.add_argument("--check", action="store_true", help="vérifie l'installation, ne change rien")
    args = parser.parse_args()

    step("Vérification des prérequis")
    claude_bin()
    say(f"{platform.system()}, Python {platform.python_version()} et Claude Code : OK")

    cfg = load_or_create_config(args.check)
    gateway = cfg["gateway_url"].rstrip("/")
    srv = cfg["servers"][0]
    name = args.name or srv["name"]
    server = srv["gateway_server"]

    if args.check:
        step(f"État de « {name} » dans Claude Code")
        if not show_server(name):
            fail(f"« {name} » n'est pas configuré.")
        return

    step("Test de la passerelle")
    code, _ = http_get(f"{gateway}/health/liveliness", timeout=15)
    if code != 200:
        fail(f"La passerelle ne répond pas (code {code}). Vérifie ta connexion, le VPN, "
             f"ou l'adresse dans {CONFIG_FILE}.")
    say("Passerelle joignable")

    step("Clé d'accès")
    cli_auth, _ = http_get(f"{gateway}/.well-known/litellm-cli-auth", timeout=10)
    if cli_auth == 200:
        say("La passerelle propose le login par la CLI : ce chemin n'est pas encore pris en charge "
            "par ce setup (voir README, « Évolutions »). Passage par l'interface.")
    say("Ouverture de la page des clés. Crée une clé (« + Create New Key ») avec les réglages "
        "indiqués dans le README, puis copie-la.")
    webbrowser.open(f"{gateway}/ui/api-keys")
    time.sleep(2)
    key = ask("Colle ici la clé que tu viens de créer (elle commence par sk-). "
              "Elle ne sera affichée nulle part.", hidden=True)
    if not key.startswith("sk-"):
        fail("La valeur collée ne ressemble pas à une clé (elle doit commencer par sk-).")

    step("Vérification des droits de la clé")
    code, body = http_get(
        f"{gateway}/mcp-rest/tools/list",
        headers={"x-litellm-api-key": f"Bearer {key}", "x-mcp-servers": server},
        timeout=30,
    )
    if code in (401, 403):
        fail(f"La passerelle a refusé la clé (code {code}). Vérifie que tu l'as copiée en entier "
             "et qu'elle est active.")
    if code != 200:
        fail(f"Réponse inattendue de la passerelle (code {code}) lors de la vérification des outils.")
    try:
        data = json.loads(body)
        tools = data if isinstance(data, list) else data.get("tools", [])
        count = len(tools)
    except (ValueError, AttributeError):
        fail("Réponse illisible de la passerelle lors de la vérification des outils.")
    if count == 0:
        say(f"""
✖ La clé est valide mais n'ouvre aucun outil sur « {server} ».
  Les droits sont l'intersection de la clé ET de ton équipe sur la passerelle.
  Message à envoyer à l'admin de la passerelle :

  « Bonjour, ma clé LiteLLM est valide mais ne voit aucun outil du serveur MCP {server}.
    Peux-tu autoriser ce serveur et ses outils pour mon équipe ? Merci ! »""")
        sys.exit(1)
    say(f"{count} outil(s) accessible(s)")

    step(f"Ajout de « {name} » à Claude Code (portée user : disponible dans tous tes dossiers)")
    claude("mcp", "remove", name, "-s", "user", quiet=True)
    res = claude(
        "mcp", "add", "--transport", "http", "--scope", "user", name, f"{gateway}/mcp",
        "--header", f"x-litellm-api-key: Bearer {key}",
        "--header", f"x-mcp-servers: {server}",
        quiet=True,
    )
    del key
    if res.returncode != 0:
        fail("Claude Code a refusé l'ajout du serveur. Relance le setup ; si ça persiste, "
             "vérifie que Claude Code est à jour.")
    show_server(name)

    step("Terminé")
    say(f"Ouvre une NOUVELLE session Claude Code : les outils « {name} » y seront chargés.")
    say("Si /mcp propose « Re-authenticate », ignore-le : ce n'est pas nécessaire.")


if __name__ == "__main__":
    main()
