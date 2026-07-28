#!/usr/bin/env bash
# FastAPI JSON API (game + admin surfaces) with hot reload on code changes.
# --reload-dir keeps the watcher on the code: the game data written under test/test-games
# would otherwise restart the server every time a turn is processed.
uv run uvicorn arena.api.app:app --reload --reload-dir arena --port 8000