"""
Admin API surface: lower-level operations for the director/admin interface.

Creating games, processing turns, and inspecting command-file readiness. Backed by
AdminService, which is allowed to reach lower into the engine than the game surface.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from arena.app.services import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])
service = AdminService()


class NewGameBody(BaseModel):
    name: str
    ship_init_file: str


@router.post("/games")
def create_game(body: NewGameBody):
    service.create_game(body.name, body.ship_init_file)
    return {"created": body.name}


@router.post("/{game}/process")
def process_turn(game: str):
    service.process_turn(game)
    return {"processed": game}


@router.get("/{game}/status")
def command_status(game: str) -> dict[str, bool]:
    return service.command_status(game)