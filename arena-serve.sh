#!/usr/bin/env bash
# Everything from one WSGI app, the way a single-app host runs it: admin pages at /, the game
# UI at /play/ and the JSON API at /api/. No hot reloading - use arena-api.sh plus
# arena-game-ui.sh for that. Needs a build first:
#
#   npm run build --prefix game-ui
#
GAME_UI_URL="${GAME_UI_URL:-/play}" uv run python arena/serve.py