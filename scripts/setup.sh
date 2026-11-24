#!/usr/bin/env bash
# Connecte un serveur MCP de la passerelle LiteLLM Liora à Claude Code, sans terminal.
#
#   scripts/setup.sh                 configure le serveur par défaut (liora-db)
#   scripts/setup.sh --name test-db  configure sous un autre nom (tests)
#   scripts/setup.sh --check         vérifie l'installation, ne change rien
#
# Le script est pensé pour être lancé par Claude Code. Toutes les saisies passent par
# des fenêtres macOS, et la clé n'est jamais affichée : elle va directement de la
# fenêtre de saisie à la config de Claude Code (~/.claude.json, portée « user »).
# Aucune valeur interne (adresse de la passerelle, nom de serveur) n'est dans ce
# repo : elles sont dans ~/.config/liora-mcp/config.json, rempli au premier lancement.
set -euo pipefail

CONFIG_FILE="${LIORA_MCP_CONFIG:-${HOME}/.config/liora-mcp/config.json}"
CONFIG_DIR="$(dirname "$CONFIG_FILE")"
MODE=setup
NAME_OVERRIDE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --name)  NAME_OVERRIDE="$2"; shift 2 ;;
    --check) MODE=check; shift ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Argument inconnu : $1" >&2; exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
step() { printf '\n▶ %s\n' "$*"; }
fail() { printf '\n✖ %s\n' "$*" >&2; exit 1; }

# Fenêtre de dialogue macOS. $1 = message, $2 = valeur par défaut, $3 = "hidden" pour masquer.
ask() {
  local msg="$1" def="${2:-}" hidden="${3:-}" extra=""
  [ "$hidden" = "hidden" ] && extra=" with hidden answer"
  osascript -e 'tell application "System Events" to activate' -e "text returned of (display dialog \"${msg}\" default answer \"${def}\"${extra} buttons {\"Annuler\", \"Valider\"} default button \"Valider\" cancel button \"Annuler\" with title \"Liora MCP setup\" giving up after 900)" 2>/dev/null \
    || fail "Saisie annulée."
}

# Lecture d'un champ du fichier de config (JSON) sans dépendance : JavaScript for Automation.
cfg() {
  osascript -l JavaScript -e "
    const c = JSON.parse(\$.NSString.stringWithContentsOfFileEncodingError('${CONFIG_FILE}', 4, null).js);
    const s = c.servers[0];
    ({gateway_url: c.gateway_url, keys_page: c.gateway_url.replace(/\/\$/, '') + '/ui/api-keys',
      name: s.name, server: s.gateway_server})['$1'];"
}

# ── 0. Prérequis ──────────────────────────────────────────────────────────────
step "Vérification des prérequis"
[ "$(uname -s)" = "Darwin" ] || fail "Ce setup est prévu pour macOS."
command -v claude >/dev/null 2>&1 || fail "La commande « claude » est introuvable. Installe Claude Code : https://claude.com/claude-code (puis relance ce setup)."
command -v curl   >/dev/null 2>&1 || fail "curl est introuvable."
say "macOS, Claude Code et curl : OK"

# ── 1. Configuration (une seule fois par poste) ───────────────────────────────
step "Configuration de la passerelle"
if [ ! -f "$CONFIG_FILE" ]; then
  [ "$MODE" = "check" ] && fail "Pas de configuration ($CONFIG_FILE). Lance le setup sans --check."
  say "Premier lancement : deux valeurs à recopier depuis la page interne « Liora MCP » (Notion de l'équipe)."
  GW=$(ask "Adresse de la passerelle (ex. https://ai-gateway.exemple.tech) :" "https://")
  SRV=$(ask "Nom du serveur MCP sur la passerelle (champ « serveur ») :" "")
  case "$GW" in https://*) ;; *) fail "L'adresse doit commencer par https://";; esac
  [ -n "$SRV" ] || fail "Nom de serveur vide."
  mkdir -p "$CONFIG_DIR"
  cat > "$CONFIG_FILE" <<EOF
{
  "gateway_url": "${GW%/}",
  "servers": [
    { "name": "liora-db", "gateway_server": "${SRV}", "description": "Entrepôt de données Nexus (lecture seule)" }
  ]
}
EOF
  chmod 600 "$CONFIG_FILE"
  say "Configuration enregistrée dans $CONFIG_FILE"
else
  say "Configuration trouvée : $CONFIG_FILE"
fi

GATEWAY=$(cfg gateway_url)
KEYS_PAGE=$(cfg keys_page)
SERVER=$(cfg server)
NAME="${NAME_OVERRIDE:-$(cfg name)}"
MCP_URL="${GATEWAY%/}/mcp"

# ── Mode --check ──────────────────────────────────────────────────────────────
if [ "$MODE" = "check" ]; then
  step "État de « ${NAME} » dans Claude Code"
  claude mcp get "$NAME" 2>&1 | grep -v -i "x-litellm-api-key" || fail "« ${NAME} » n'est pas configuré."
  exit 0
fi

# ── 2. La passerelle répond ? ─────────────────────────────────────────────────
step "Test de la passerelle"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "${GATEWAY%/}/health/liveliness" || true)
[ "$code" = "200" ] || fail "La passerelle ne répond pas (code ${code}). Vérifie le VPN ou l'adresse dans $CONFIG_FILE."
say "Passerelle joignable"

# ── 3. Clé d'accès ────────────────────────────────────────────────────────────
# Chemin sans clic (CLI LiteLLM + login navigateur) : activé seulement si la passerelle
# l'expose. Sinon, variante de secours : la personne crée la clé dans l'interface.
step "Clé d'accès"
cli_auth=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${GATEWAY%/}/.well-known/litellm-cli-auth" || true)
if [ "$cli_auth" = "200" ]; then
  say "La passerelle propose le login par la CLI : ce chemin n'est pas encore pris en charge par ce setup (voir README, « Évolutions »). Passage par l'interface."
fi
say "Ouverture de la page des clés. Crée une clé (« + Create New Key ») avec les réglages indiqués dans le README, puis copie-la."
open "$KEYS_PAGE"
sleep 2
KEY=$(ask "Colle ici la clé que tu viens de créer (elle commence par sk-). Elle ne sera affichée nulle part." "" hidden)
case "$KEY" in sk-*) ;; *) unset KEY; fail "La valeur collée ne ressemble pas à une clé (elle doit commencer par sk-).";; esac

# ── 4. La clé ouvre-t-elle des outils ? ───────────────────────────────────────
step "Vérification des droits de la clé"
resp=$(curl -s --max-time 30 -w '\n%{http_code}' -H "x-litellm-api-key: Bearer ${KEY}" -H "x-mcp-servers: ${SERVER}" "${GATEWAY%/}/mcp-rest/tools/list" || true)
http=$(printf '%s' "$resp" | tail -n 1)
body=$(printf '%s' "$resp" | sed '$d')
if [ "$http" = "401" ] || [ "$http" = "403" ]; then
  unset KEY; fail "La passerelle a refusé la clé (code ${http}). Vérifie que tu l'as copiée en entier et qu'elle est active."
fi
[ "$http" = "200" ] || { unset KEY; fail "Réponse inattendue de la passerelle (code ${http}) lors de la vérification des outils."; }
count=$(printf '%s' "$body" | osascript -l JavaScript -e '
  function run() {
    const raw = $.NSString.alloc.initWithDataEncoding($.NSFileHandle.fileHandleWithStandardInput.readDataToEndOfFile, 4).js;
    try { const j = JSON.parse(raw); const t = Array.isArray(j) ? j : (j.tools || []); return String(t.length); }
    catch (e) { return "erreur"; }
  }' 2>/dev/null || echo erreur)
if [ "$count" = "erreur" ]; then
  unset KEY; fail "Réponse illisible de la passerelle lors de la vérification des outils."
fi
if [ "$count" = "0" ]; then
  unset KEY
  cat <<EOF

✖ La clé est valide mais n'ouvre aucun outil sur « ${SERVER} ».
  Les droits sont l'intersection de la clé ET de ton équipe sur la passerelle.
  Message à envoyer à l'admin de la passerelle :

  « Bonjour, ma clé LiteLLM est valide mais ne voit aucun outil du serveur MCP ${SERVER}.
    Peux-tu autoriser ce serveur et ses outils pour mon équipe ? Merci ! »
EOF
  exit 1
fi
say "${count} outil(s) accessible(s)"

# ── 5. Branchement dans Claude Code ───────────────────────────────────────────
step "Ajout de « ${NAME} » à Claude Code (portée user : disponible dans tous tes dossiers)"
claude mcp remove "$NAME" -s user >/dev/null 2>&1 || true
claude mcp add --transport http --scope user "$NAME" "$MCP_URL" \
  --header "x-litellm-api-key: Bearer ${KEY}" \
  --header "x-mcp-servers: ${SERVER}" >/dev/null
unset KEY
claude mcp get "$NAME" 2>&1 | grep -v -i "x-litellm-api-key" || true

step "Terminé"
say "Ouvre une NOUVELLE session Claude Code : les outils « ${NAME} » y seront chargés."
say "Si /mcp propose « Re-authenticate », ignore-le : ce n'est pas nécessaire."
