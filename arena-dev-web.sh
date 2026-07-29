#!/usr/bin/env bash
# Flask admin/director pages with reloading. The game UI is not served from here, so point its
# links at the Vite dev server (arena-game-ui.sh).
GAME_UI_URL="${GAME_UI_URL:-http://localhost:5173}" \
  uv run flask --app arena.admin_ui.app:app --debug run