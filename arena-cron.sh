#!/usr/bin/env bash
# Run one of the jobs that happen on a clock. Hook them into cron:
#
#     0  * * * * /home/you/starship-arena/arena-cron.sh
#     30 * * * * /home/you/starship-arena/arena-cron.sh remind_due
#
# The run writes itself to logs/arena.log, which rotates. Anything that fails before that, a
# missing venv or a broken import, goes to whatever the host does with a task's output.
#
# `process_due` processes every game whose settings name this hour, so the cron schedule is the
# clock: `process_hours 8 20` runs on those two passes, `*` runs on every pass, and a game with
# none is left to the director. A due game processes whether the orders are in or not: anyone who
# did not send any gets an empty command file, which reads as no orders arriving in time.
#
# `remind_due` pokes whoever still owes orders and asked to be poked. On the half hour it reaches
# them in time for the hour a game processes on. It keeps to one reminder each per round through
# the journal rather than the clock, so run it as often as suits.
#
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

ACTION="${1:-process_due}"
VENV="$HOME/.virtualenvs/${VENV_NAME:-starship-arena}"

if [ -x "$VENV/bin/python" ]; then
    "$VENV/bin/python" -m arena.cli.main "$ACTION"
elif command -v uv > /dev/null 2>&1; then
    uv run python -m arena.cli.main "$ACTION"
else
    python3 -m arena.cli.main "$ACTION"
fi