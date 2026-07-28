"""
Game API surface: player-facing, restricted operations.

Reads ship/round state for viewing and time-travel, and validates/saves move plans.
Backed by the UI-agnostic GameService; returns its DTOs directly (FastAPI serialises them).
"""

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from arena.app.dto import GameSummary, ShipRound, PlayerPlan, GameOverview
from arena.app.services import GameService

router = APIRouter(prefix="/api/game", tags=["game"])
service = GameService()


class CommandsBody(BaseModel):
    lines: list[str]


@router.get("/games")
def list_games() -> list[GameSummary]:
    return service.list_games()


@router.get("/{game}/ships")
def list_ships(game: str) -> list[str]:
    return service.list_ships(game)


@router.get("/{game}/ships/{ship}/rounds/{round_nr}")
def ship_round(game: str, ship: str, round_nr: int) -> ShipRound:
    try:
        return service.get_ship_round(game, ship, round_nr)
    except (KeyError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=f"No data for {ship} in {game} round {round_nr}: {e}")


@router.get("/{game}/overview")
def game_overview(game: str) -> GameOverview:
    try:
        return service.game_overview(game)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{game}/players/{player}/plan")
def player_plan(game: str, player: str, round: int | None = None) -> PlayerPlan:
    """The player's picture at the end of a round; the last round if none is given."""
    try:
        return service.get_player_plan(game, player, round)
    except (KeyError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{game}/ships/{ship}/commands")
def get_commands(game: str, ship: str) -> list[str]:
    return service.get_commands(game, ship)


@router.post("/{game}/ships/{ship}/commands")
def post_commands(game: str, ship: str, body: CommandsBody, response: Response):
    checks = service.check_commands(game, ship, body.lines)
    all_ok = all(c.ok for c in checks)
    if all_ok:
        service.save_commands(game, ship, body.lines)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return {"ok": all_ok, "checks": checks}