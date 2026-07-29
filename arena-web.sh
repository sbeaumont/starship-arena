#!/usr/bin/env bash
# Flask admin/director pages on their own. The game UI is not served from here, so point its
# links at the Vite dev server (arena-game-ui.sh).
GAME_UI_URL="${GAME_UI_URL:-http://localhost:5173}" \
  uv run flask --app arena.admin_ui.app:app run --host=0.0.0.0 -p 8080