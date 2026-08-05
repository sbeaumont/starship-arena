#!/usr/bin/env bash
# Everything from one WSGI app, exactly as a deployed host runs it: the game UI at /, the admin
# pages at /director/ and the JSON API at /api/. No configuration needed - the defaults are the
# deployed ones. No hot reloading either; use arena-dev.sh for that.
#
# Needs a build first:  npm run build --prefix game-ui
#
uv run python -m arena.serve