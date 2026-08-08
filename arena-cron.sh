#!/usr/bin/env bash
# Process every game whose settings name this hour. Hook it into cron on the hour:
#
#     0 * * * * /home/you/starship-arena/arena-cron.sh
#
# The run writes itself to logs/arena.log, which rotates. Anything that fails before that, a
# missing venv or a broken import, goes to whatever the host does with a task's output.
#
# The cron schedule is the clock. `process_hours 8 20` runs on those two passes, `*` runs on every
# pass, and a game with none is left to the director.
#
# A due game processes whether the orders are in or not: anyone who did not send any gets an empty
# command file, which reads as no orders arriving in time.
#
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

VENV="$HOME/.virtualenvs/${VENV_NAME:-starship-arena}"

if [ -x "$VENV/bin/python" ]; then
    "$VENV/bin/python" -m arena.cli.main process_due
elif command -v uv > /dev/null 2>&1; then
    uv run python -m arena.cli.main process_due
else
    python3 -m arena.cli.main process_due
fi