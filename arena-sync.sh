#!/usr/bin/env bash
# Bring this machine's environment in line with what the project depends on.
#
#     ./arena-sync.sh
#
# Development has uv, where this is `uv sync`. The host has a plain virtualenv and no uv, so
# there it is pip and requirements.txt. Either way, the answer to "the host is missing a package"
# is to run this rather than to work out which package it was.
#
# arena-deploy.sh runs it on the host between the pull and the reload, so a dependency added here
# arrives there without anybody typing its name a second time.
set -euo pipefail

# Run from the repository, because that is where both dependency files are.
cd "$(dirname "${BASH_SOURCE[0]}")"

VENV="$HOME/.virtualenvs/${VENV_NAME:-starship-arena}"

# uv first, unlike its sibling scripts. They want an interpreter, and on the host the virtualenv
# is the one that works. This wants whatever owns the environment, and where uv exists that is uv.
if command -v uv > /dev/null 2>&1; then
    exec uv sync
fi

if [ ! -x "$VENV/bin/python" ]; then
    echo "No uv, and no virtualenv at $VENV. Nothing here to sync." >&2
    exit 1
fi

echo "Installing into $VENV..."
# Nothing is upgraded that already satisfies its floor, which is what makes this safe to run on
# every deploy.
"$VENV/bin/python" -m pip install -r requirements.txt