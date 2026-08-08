"""
Game API surface: player-facing, restricted operations.

Reads ship/round state for viewing and time-travel, and validates/saves move plans.
Backed by the UI-agnostic GameService; returns its DTOs directly (FastAPI serialises them).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from arena.app.dto import (GameSummary, OpenGame, ShipRound, PlayerPlan, GameOverview,
                           ShipTypeInfo, Me, Pulse, ServerTime)
from arena.app.players import LOGIN_COOKIE, LOGIN_COOKIE_MAX_AGE, Player
from arena.app.services import GameService

router = APIRouter(prefix="/api/game", tags=["game"])
service = GameService()

class CommandsBody(BaseModel):
    lines: list[str]


class LoginBody(BaseModel):
    token: str


class RegisterBody(BaseModel):
    name: str


class RegistrationBody(BaseModel):
    names: list[str]


def logged_in(request: Request) -> Player | None:
    return service.resolve_login(request.cookies.get(LOGIN_COOKIE))


def require_login(request: Request) -> Player:
    player = logged_in(request)
    if player is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return player


def require_own_ship(game: str, ship: str, me: Player) -> None:
    if me.is_director:
        return
    if service.ship_owner(game, ship) != me.name:
        raise HTTPException(status_code=403, detail=f"{ship} is not yours.")


def _remember(response: Response, player: Player) -> None:
    response.set_cookie(LOGIN_COOKIE, player.token, max_age=LOGIN_COOKIE_MAX_AGE,
                        httponly=True, samesite='lax', secure=True)


@router.post("/login")
def login(body: LoginBody, response: Response) -> Me:
    player = service.resolve_login(body.token)
    if player is None:
        raise HTTPException(status_code=401, detail="That link no longer works.")
    _remember(response, player)
    return service.me(player)


@router.post("/register")
def register(body: RegisterBody, response: Response) -> Me:
    """Claim a name that no game is using yet, and be logged in as it."""
    try:
        player = service.register_player(body.name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    _remember(response, player)
    return service.me(player)


@router.get("/me")
def whoami(me: Player = Depends(require_login)) -> Me:
    return service.me(me)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(LOGIN_COOKIE)
    return {"ok": True}


@router.get("/games")
def list_games() -> list[GameSummary]:
    return service.list_games()


@router.get("/time")
def server_time() -> ServerTime:
    """The server's clock, so a reader can put a game's processing hours beside their own."""
    return service.server_time()


@router.get("/ship-types")
def list_ship_types() -> list[ShipTypeInfo]:
    return service.list_ship_types()


@router.get("/manual")
def manual() -> Response:
    return Response(content=service.manual(), media_type="application/pdf")


@router.get("/open")
def open_games(me: Player = Depends(require_login)) -> list[OpenGame]:
    return service.open_games(me.name)


@router.put("/open/{game}")
def register(game: str, body: RegistrationBody, me: Player = Depends(require_login)) -> OpenGame:
    try:
        service.register(game, me.name, [n.strip() for n in body.names if n.strip()])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return next(g for g in service.open_games(me.name) if g.name == game)


@router.delete("/open/{game}")
def withdraw(game: str, me: Player = Depends(require_login)) -> OpenGame:
    service.withdraw(game, me.name)
    return next(g for g in service.open_games(me.name) if g.name == game)


@router.get("/{game}/ships")
def list_ships(game: str) -> list[str]:
    return service.list_ships(game)


@router.get("/{game}/ships/{ship}/rounds/{round_nr}")
def ship_round(game: str, ship: str, round_nr: int, me: Player = Depends(require_login)) -> ShipRound:
    require_own_ship(game, ship, me)
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
def player_plan(game: str, player: str, round: int | None = None,
                me: Player = Depends(require_login)) -> PlayerPlan:
    """The player's picture at the end of a round; the last round if none is given."""
    if not (me.is_director or me.name == player):
        raise HTTPException(status_code=403, detail=f"{player}'s picture is not yours to see.")
    try:
        return service.get_player_plan(game, player, round)
    except (KeyError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{game}/pulse")
def pulse(game: str, me: Player = Depends(require_login)) -> Pulse:
    """Polled while a player waits: has the round moved on, and who has said they are ready."""
    return service.pulse(game, me.name)


class ReadyBody(BaseModel):
    ready: bool


@router.post("/{game}/players/{player}/ready")
def set_ready(game: str, player: str, body: ReadyBody, me: Player = Depends(require_login)) -> dict:
    """Saying you are done with the round, which is not the same as having saved orders."""
    if not (me.is_director or me.name == player):
        raise HTTPException(status_code=403, detail=f"{player} is not you.")
    processed = service.set_ready(game, player, body.ready)
    return {"ready": service.is_ready(game, player), "processed": processed}


@router.get("/{game}/ships/{ship}/commands")
def get_commands(game: str, ship: str, me: Player = Depends(require_login)) -> list[str]:
    require_own_ship(game, ship, me)
    return service.get_commands(game, ship)


@router.post("/{game}/ships/{ship}/commands")
def post_commands(game: str, ship: str, body: CommandsBody, response: Response,
                  me: Player = Depends(require_login)):
    require_own_ship(game, ship, me)
    checks = service.check_commands(game, ship, body.lines)
    all_ok = all(c.ok for c in checks)
    if all_ok:
        service.save_commands(game, ship, body.lines)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
    return {"ok": all_ok, "checks": checks}