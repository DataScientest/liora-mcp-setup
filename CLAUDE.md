# liora-mcp-setup

Ce repo installe et connecte à Claude Code les serveurs MCP de la passerelle LiteLLM de Liora (aujourd'hui : `liora-db`, l'entrepôt de données Nexus en lecture seule). Il s'adresse à des personnes non techniques : elles ouvrent le repo et disent « installe LiteLLM et le MCP ».

## Quand l'utilisateur demande d'installer, de connecter ou de réparer le MCP

Utilise le skill `liora-mcp-setup` (`.claude/skills/liora-mcp-setup/SKILL.md`). Il lance `uv run scripts/setup.py`, qui fait tout le travail avec des fenêtres de saisie, sur macOS, Windows et Linux.

## Règles du repo

- Le repo est **public**. Il ne contient aucune valeur interne : ni adresse de passerelle, ni nom de serveur, ni identifiant de projet, ni clé. Les valeurs réelles vivent dans `~/.config/liora-mcp/config.json` sur chaque poste.
- Personne ne colle de clé dans le chat. La clé passe uniquement par la fenêtre de saisie du script.
- Données : le MCP `liora-db` donne accès à des données d'apprenants. On n'en sort que des chiffres agrégés, jamais de donnée nominative.
- Rédaction en français, phrases courtes, sans jargon pour l'utilisateur final.
