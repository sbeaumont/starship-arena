#!/usr/bin/env bash
# All three development servers in one terminal, with hot reloading:
#
#   api   :8000  FastAPI, reloads on Python changes
#   ui    :5173  Vite, hot module reload for the Svelte game UI
#   admin :8080  Flask director console, reloads on Python and template changes
#
# Open http://localhost:5173 for the game UI and http://localhost:8080 for the console; the
# console's "map" links point at :5173, which is why all three belong up together.
#
# Ctrl-C stops all of them. For a single process without hot reloading - the way a host runs
# it - use arena-serve.sh instead.
#
set -euo pipefail

CYAN=$'\033[36m'; GREEN=$'\033[32m'; AMBER=$'\033[33m'; OFF=$'\033[0m'

# Tag every line as it arrives. `read` is line-buffered by nature, which keeps the three
# streams from interleaving mid-line the way a `sed` pipe would.
prefix() {
    while IFS= read -r line; do
        printf '%s%-5s%s %s\n' "$2" "$1" "$OFF" "$line"
    done
}

# Python buffers its output when it is writing to a pipe rather than a terminal, and these are
# all writing to pipes now.
export PYTHONUNBUFFERED=1

# Development is http, and a browser drops a Secure cookie on anything but https and localhost.
# Without this the map opens fine on this machine and answers 401 to a phone on the network.
# Only ever set here.
export ARENA_INSECURE_COOKIES=1

# Ctrl-C reaches this shell only; kill the whole process group so no server is left holding a
# port. Without this you get "address already in use" on the next run.
trap 'kill 0' EXIT

# The console is a separate server here, so the API has to be told where it is.
ADMIN_UI_URL="${ADMIN_UI_URL:-http://localhost:8080}" \
    uv run uvicorn arena.api.app:app --reload --reload-dir arena --port 8000 2>&1 \
    | prefix api "$CYAN" &

npm run dev --prefix game-ui 2>&1 \
    | prefix ui "$GREEN" &

GAME_UI_URL="${GAME_UI_URL:-http://localhost:5173}" \
    uv run flask --app arena.admin_ui.app:app run --host=0.0.0.0 -p 8080 --reload 2>&1 \
    | prefix admin "$AMBER" &

wait