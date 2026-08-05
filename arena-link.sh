#!/usr/bin/env bash
# Login links. The address is the game UI's own, wherever you are running it:
#
#     ./arena-link.sh                                            who can log in
#     ./arena-link.sh Serge https://your.site --director         the director, deployed
#     ./arena-link.sh Menno http://localhost:5173                arena-dev.sh (Vite)
#     ./arena-link.sh Menno http://localhost:8080                arena-serve.sh
#
# Set the address players use once, in secret.py, and leave it off from then on:
#
#     SITE_URL = 'https://your.site'
#
# That is the address the link is *for*, not the one this machine serves from - a link goes to
# somebody else. Pass an address when you want one pointing somewhere else, like a local server
# to try it out on; given, it wins.
#
# Issuing again replaces the link somebody had, so this is also how a lost or leaked one is
# replaced. The first director's link has to be made here: the console will not let anyone in
# until a director exists.
#
set -euo pipefail

# Run from the repository, because `python -m arena.cli.main` finds the packages through the
# working directory.
cd "$(dirname "${BASH_SOURCE[0]}")"

VENV="$HOME/.virtualenvs/${VENV_NAME:-starship-arena}"

if [ $# -eq 0 ]; then
    ACTION=(players)
else
    ACTION=(link --name "$1")
    shift
    URL=""
    for arg in "$@"; do
        case "$arg" in
            -*) ACTION+=("$arg") ;;   # --director
            *)  URL="$arg" ;;
        esac
    done
    ACTION+=(--url "$URL")
fi

# The host has a plain virtualenv (see pythonanywhere-setup.sh); development has uv.
if [ -x "$VENV/bin/python" ]; then
    "$VENV/bin/python" -m arena.cli.main "${ACTION[@]}"
elif command -v uv > /dev/null 2>&1; then
    uv run python -m arena.cli.main "${ACTION[@]}"
else
    python3 -m arena.cli.main "${ACTION[@]}"
fi