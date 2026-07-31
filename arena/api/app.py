"""The JSON API, serving the player's game UI at /api/game.

Speaks only in the DTOs of arena/app, never in engine objects. See docs/architecture.md.

Run with: uv run uvicorn arena.api.app:app --reload"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arena.api.game import router as game_router

app = FastAPI(title="Starship Arena API")

# The Svelte game UI runs on its own dev server (Vite, default :5173) during development,
# a different origin, so the browser needs CORS permission to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}