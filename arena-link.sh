#!/usr/bin/env bash
# Login links. The address is the game UI's own, wherever you are running it:
#
#     ./arena-link.sh                                                who can log in
#     ./arena-link.sh Serge https://your.site/play --director        the director, deployed
#     ./arena-link.sh Menno http://localhost:5173                    arena-dev.sh (Vite)
#     ./arena-link.sh Menno http://localhost:8080/play               arena-serve.sh
#     ./arena-link.sh Menno                                          just the path
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