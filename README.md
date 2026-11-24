# liora-mcp-setup

Connecte les outils de la passerelle IA de Liora à Claude Code, sans taper une seule commande.

Aujourd'hui, un seul outil : **`liora-db`**, l'entrepôt de données de Nexus en lecture seule (inscriptions, cohortes, modules, progression, feedbacks). D'autres outils et des skills de la passerelle viendront s'ajouter ici.

## Avant de commencer

### Une fois pour toute l'équipe (référent ou admin de la passerelle)

1. **Page interne « Liora MCP ».** Créer une page interne (Notion ou Drive, non publique) qui donne deux valeurs : l'adresse de la passerelle et le nom du serveur MCP sur la passerelle. Le setup les demande au premier lancement. Ce repo étant public, il ne les contient pas.
2. **Droits sur la passerelle.** Les droits d'une clé sont l'intersection de la clé **et** de l'équipe. L'équipe de chaque utilisateur doit donc autoriser le serveur MCP et ses outils.

### Pour chaque personne

- un Mac ;
- Claude Code installé et connecté ;
- un compte sur la passerelle IA de Liora, rattaché à une équipe qui a les droits ci-dessus ;
- l'accès à la page interne « Liora MCP ».

## Installer (5 minutes, une seule fois)

1. Ouvre ce dossier dans Claude Code.
2. Écris : **« installe LiteLLM et le MCP »**.
3. Suis les fenêtres qui s'ouvrent :
   - au premier lancement, deux valeurs à recopier depuis la page interne « Liora MCP » (adresse de la passerelle et nom du serveur) ;
   - une page de la passerelle s'ouvre : crée ta clé (voir ci-dessous), puis colle-la **dans la fenêtre**, jamais dans le chat.
4. Ouvre une nouvelle session Claude Code. Les outils `liora-db` y sont chargés.

Si `/mcp` te propose « Re-authenticate », ignore-le : ce n'est pas nécessaire.

## Créer la clé

Dans la page **Virtual Keys** de la passerelle, clique sur **+ Create New Key** :

| Champ | Valeur |
|---|---|
| Owned By | You |
| Team | ton équipe sur la passerelle |
| Key Name | `claude-code-liora-db` |
| Models | rien |
| Optional Settings → MCP Servers | uniquement le serveur indiqué sur la page « Liora MCP » |

Clique sur **Create Key**, puis copie la clé affichée : elle n'apparaît qu'une seule fois.

## Si ça ne marche pas

| Message | Ce qu'il faut faire |
|---|---|
| « La passerelle ne répond pas » | Vérifie ta connexion (et le VPN si besoin), puis relance. |
| « La passerelle a refusé la clé » | La clé est mal copiée ou désactivée. Crée-en une nouvelle et relance. |
| « La clé n'ouvre aucun outil » | Tes droits viennent de la clé **et** de ton équipe. Envoie à l'admin de la passerelle le message que le setup affiche. |
| « claude introuvable » | Installe Claude Code, puis relance. |

Pour vérifier une installation sans rien changer, demande à Claude : « vérifie mon installation du MCP ».

## Règles d'usage

- `liora-db` contient des données d'apprenants. On n'en sort que des **chiffres agrégés**, jamais de nom, d'email ni d'entreprise.
- Ne colle jamais ta clé dans le chat ou dans un fichier du repo. Si c'est arrivé, révoque-la dans la passerelle et crée-en une autre.

## Comment ça marche

- `scripts/setup.sh` fait tout le travail. Il pose les questions dans des fenêtres macOS, vérifie que la clé ouvre bien des outils, puis ajoute le serveur à Claude Code en portée « user », donc disponible dans tous tes dossiers.
- La clé va directement de la fenêtre de saisie à la config de Claude Code (`~/.claude.json`). Ni le script, ni Claude, ni ce repo ne l'affichent.
- Les valeurs internes (adresse, nom du serveur) sont stockées sur ton poste dans `~/.config/liora-mcp/config.json`. Ce repo étant public, il n'en contient aucune.

## Évolutions

- **Login sans clic.** La CLI LiteLLM (`lite login`) permettrait de se connecter d'un clic dans le navigateur et de générer la clé automatiquement, sans passer par l'interface. Il faut que la passerelle expose le login CLI (`/.well-known/litellm-cli-auth`, PKCE). Le setup détecte déjà si c'est le cas. Ce chemin sera ajouté dès qu'il pourra être testé.
- **Plusieurs serveurs.** Le fichier de config accepte une liste de serveurs. Pour l'instant, le setup configure le premier.

### Message pour l'admin de la passerelle

> Bonjour, pour simplifier l'onboarding de l'équipe pédagogique sur la passerelle, est-ce que tu pourrais activer le login par la CLI LiteLLM (`lite login` en PKCE, endpoint `/.well-known/litellm-cli-auth`, et `EXPERIMENTAL_UI_LOGIN` si nécessaire) ? Idéalement avec le SSO Google. Chacun pourrait alors se connecter d'un clic et obtenir sa clé MCP sans passer par l'interface. Merci !
