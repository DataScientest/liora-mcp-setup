---
name: liora-mcp-setup
description: Install and connect the Liora LiteLLM gateway's MCP servers (for example liora-db) to Claude Code for a non-technical user. Use when the user asks to install, set up, connect or repair LiteLLM, the MCP, liora-db or "les outils de la passerelle", or says a liora MCP shows no tools.
---

# Connect a Liora gateway MCP server

The user is usually not technical. Do the work; never hand them shell commands to type.

## Run the setup

1. Run `scripts/setup.sh` from the repo root with the Bash tool and `run_in_background: true` (the user may need several minutes; you are notified when it exits, then read its output). The script opens macOS dialogs and a browser tab; the user answers them. Tell the user in one line beforehand: "Des fenêtres vont s'ouvrir : suis-les, je m'occupe du reste."
2. On first run the script asks for two values (gateway address, server name). They are on the team's internal « Liora MCP » page. If the user does not have them, stop and tell them to ask the gateway admin. Never guess them.
3. When the browser opens on the keys page, tell the user to create a key with the settings listed in `README.md` (section « Créer la clé »), then to paste it **in the dialog**, never in the chat.

## Hard rules

- Never ask for, read, print or store the API key yourself. If the user pastes a key in the chat, tell them to revoke it in the gateway and create a new one.
- Never run `lite login --config-claude` or `lite up`: they reroute Claude Code's own traffic through the gateway.
- Never commit `~/.config/liora-mcp/config.json` or any gateway address to this repo (it is public).
- Do not verify with `claude -p` (headless auth may be expired). The script verifies the tool count itself.

## After the script

- Success: tell the user to open a **new** Claude Code session (or start one for them if a session-starting tool is available) and to ignore any « Re-authenticate » prompt in `/mcp`.
- "0 outil": the key is valid but key × team rights exclude the tools. Show the message the script printed and tell the user to send it to the gateway admin.
- Other failures: read the script's last `✖` line, explain it in one sentence, fix what you can, rerun.
- To check an existing install without changing anything: `scripts/setup.sh --check`.

## Adding a server later

Servers are listed in `config.example.json` / `~/.config/liora-mcp/config.json` under `servers`. v1 sets up `servers[0]` only; see README « Évolutions ».
