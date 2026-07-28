"""
FastAPI JSON API for Starship Arena.

Pure JSON seam between the engine and the UIs. It exposes no storage details -- every
endpoint speaks in the DTOs of the application-services layer (arena/app). The API is
split into two surfaces:

    /api/game/...   player-facing, restricted (ship state, planning)
    /api/admin/...  lower-level operations for the director/admin interface

Run with:  uv run uvicorn arena.api.app:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arena.api.game import router as game_router
from arena.api.admin import router as admin_router

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
app.include_router(admin_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}