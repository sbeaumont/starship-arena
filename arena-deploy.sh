#!/usr/bin/env bash
# Deploy from your own machine: pull on the host over ssh, then reload the web app through the
# host's API. No console, no Web tab.
#
#     ./arena-deploy.sh
#
# Two per-host settings, environment first and secret.py second, the same order as everything
# else:
#
#     PA_API_TOKEN      the reload is an API call. www.pythonanywhere.com/account/#api_token
#                       ($API_TOKEN in the environment, which a console exports for itself)
#     PA_SSH_KEYFILE    the key the host knows you by, so ssh does not walk every key you own
#                       looking for it. Leave it out to let ssh and ~/.ssh/config decide.
#
# PA_USER and PA_DOMAIN are the account and the domain exactly as the Web tab spells them;
# PA_PATH is where the repository sits on the host, relative to its home directory.
set -euo pipefail

PA_USER="${PA_USER:-AgFx}"
PA_DOMAIN="${PA_DOMAIN:-game.starship-arena.net}"
PA_PATH="${PA_PATH:-starship-arena}"
RELOAD="https://www.pythonanywhere.com/api/v0/user/$PA_USER/webapps/$PA_DOMAIN/reload/"

# Run from the repository, because that is where secret.py is importable.
cd "$(dirname "${BASH_SOURCE[0]}")"

from_secret() {
    [ -f secret.py ] || return 0
    python3 -c "import secret; print(getattr(secret, '$1', ''))"
}

TOKEN="${API_TOKEN:-$(from_secret PA_API_TOKEN)}"
KEYFILE="${PA_SSH_KEYFILE:-$(from_secret PA_SSH_KEYFILE)}"

if [ -z "$TOKEN" ]; then
    echo "No API token. Put one in secret.py, from your account page:" >&2
    echo "    PA_API_TOKEN = '...'   # www.pythonanywhere.com/account/#api_token" >&2
    exit 1
fi

SSH=(ssh)
if [ -n "$KEYFILE" ]; then
    # A setting is written the way you would type it, and the shell expands ~ only in literals.
    SSH+=(-i "${KEYFILE/#\~/$HOME}" -o IdentitiesOnly=yes)
fi

# Nothing to build: game-ui/dist is committed, so the pull brings the bundle with it.
echo "Pulling on $PA_USER@ssh.pythonanywhere.com:$PA_PATH..."
"${SSH[@]}" "$PA_USER@ssh.pythonanywhere.com" "git -C '$PA_PATH' pull"

echo
echo "Reloading $PA_DOMAIN..."
curl --fail-with-body -sS -X POST -H "Authorization: Token $TOKEN" "$RELOAD"
echo