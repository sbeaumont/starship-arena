#!/usr/bin/env bash
# Deploy: pull, then reload the web app. Run it from a Bash console on the host:
#
#     ~/starship-arena/arena-deploy.sh
#
# From your own machine, if your plan has SSH, the same thing without opening a console:
#
#     ssh AgFx@ssh.pythonanywhere.com 'bash starship-arena/arena-deploy.sh'
#
# The reload is an API call, so it needs a token. Environment first, then secret.py, the same
# order as everything else per-host:
#
#     $API_TOKEN                  a PythonAnywhere console already has this one
#     PA_API_TOKEN in secret.py   anywhere else, from www.pythonanywhere.com/account/#api_token
#
# PA_USER and PA_DOMAIN are the account and the domain exactly as the Web tab spells them.
set -euo pipefail

PA_USER="${PA_USER:-AgFx}"
PA_DOMAIN="${PA_DOMAIN:-game.starship-arena.net}"
RELOAD="https://www.pythonanywhere.com/api/v0/user/$PA_USER/webapps/$PA_DOMAIN/reload/"

# Run from the repository: that is what git pull acts on, and where secret.py is importable.
cd "$(dirname "${BASH_SOURCE[0]}")"

TOKEN="${API_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f secret.py ]; then
    TOKEN="$(python3 -c "import secret; print(getattr(secret, 'PA_API_TOKEN', ''))")"
fi
if [ -z "$TOKEN" ]; then
    echo "No API token. Put one in secret.py, from your account page:" >&2
    echo "    PA_API_TOKEN = '...'   # www.pythonanywhere.com/account/#api_token" >&2
    exit 1
fi

git pull

# Nothing to build: game-ui/dist is committed, so the pull brought the bundle with it.
echo
echo "Reloading $PA_DOMAIN..."
curl --fail-with-body -sS -X POST -H "Authorization: Token $TOKEN" "$RELOAD"
echo