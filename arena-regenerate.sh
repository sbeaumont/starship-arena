#!/usr/bin/env bash
# Replay games from their ships file and orders, back to the round they were on:
#
#     ./arena-regenerate.sh                     every playable game
#     ./arena-regenerate.sh The_War_of_Noodles   one of them
#
# The data root is copied first, next to itself and stamped with the time, because a regenerate
# starts by deleting the pickles: a round whose command file is missing cannot be replayed, and
# every round after it goes with it. The run prints the round each game ends on against the round
# it was on, and stops on the first one that comes back short.
#
# What it is for: saved state written by older code, and anything else that makes the worlds on
# disk not what this code reads. A replay uses today's engine, so a game whose numbers have since
# been rebalanced comes back as today's rules would have played it.
#
# Archived games are left alone. They are not playable, so nothing reads them, and their orders may
# well be gone - which is the case where this destroys rounds rather than rebuilding them.
#
set -euo pipefail

# Run from the repository, because `python -m arena.cli.main` finds the packages through the
# working directory.
cd "$(dirname "${BASH_SOURCE[0]}")"

VENV="$HOME/.virtualenvs/${VENV_NAME:-starship-arena}"

# The host has a plain virtualenv (see pythonanywhere-setup.sh); development has uv.
if [ -x "$VENV/bin/python" ]; then
    PYTHON=("$VENV/bin/python")
elif command -v uv > /dev/null 2>&1; then
    PYTHON=(uv run python)
else
    PYTHON=(python3)
fi

# Where the data is, asked rather than assumed: the setting may be absolute or relative to here.
ROOT="$("${PYTHON[@]}" -c 'from arena.cfg import GAME_DATA_DIR; print(GAME_DATA_DIR)')"
BACKUP="$ROOT.bak-$(date +%Y%m%d-%H%M%S)"

echo "Copying $ROOT to $BACKUP..."
cp -a "$ROOT" "$BACKUP"

echo
"${PYTHON[@]}" -m arena.cli.main regenerate "$@"
echo
echo "The copy is still at $BACKUP. Delete it once the games read right."