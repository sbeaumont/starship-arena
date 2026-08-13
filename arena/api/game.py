"""
Game API surface: player-facing, restricted operations.

Reads ship/round state for viewing and time-travel, and validates/saves move plans.
Backed by the UI-agnostic GameService; returns its DTOs directly (FastAPI serialises them).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from arena.app.dto import (ValhallaGame, GameSummary, OpenGame, ShipRound, PlayerPlan, GameOverview,
                           GameReplay, ShipTypeInfo, Me, Pulse, Reminders, ServerTime, SoloGame)
from arena.app.players import LOGIN_COOKIE, LOGIN_COOKIE_MAX_AGE, LOGIN_COOKIE_SECURE, Player
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


class SoloShipBody(BaseModel):
    name: str
    type: str


class SoloBody(BaseModel):
    ships: list[SoloShipBody]


class StoryBody(BaseModel):
    text: str


class RemindersBody(BaseModel):
    """Everything off is the shape of asking for nothing, which is how a setting is turned off."""
    discord_id: str = ''
    hours_before: int = 0
    daily_hour: int | None = None
    timezone: str = ''


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
                        httponly=True, samesite='lax', secure=LOGIN_COOKIE_SECURE)


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


@router.put("/me/reminders")
def save_reminders(body: RemindersBody, me: Player = Depends(require_login)) -> Me:
    """When this player wants telling that they owe orders. Their own row, from the cookie."""
    try:
        return service.save_reminders(me, Reminders(discord_id=body.discord_id,
                                                    hours_before=body.hours_before,
                                                    daily_hour=body.daily_hour,
                                                    timezone=body.timezone))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


@router.get("/valhalla")
def valhalla_games() -> list[ValhallaGame]:
    """The games that are over and on show, and everything written about them. Open, like the
    replay of any of them."""
    return service.list_valhalla_games()


@router.put("/valhalla/{game}/story")
def save_story(game: str, body: StoryBody, me: Player = Depends(require_login)) -> ValhallaGame:
    """The caller's own account of a game they played. Never anybody else's: the name comes from
    the cookie, and the game's own file says who flew there."""
    return _write_up(game, lambda: service.save_story(game, me.name, body.text))


@router.put("/valhalla/{game}/win-story")
def save_win_story(game: str, body: StoryBody, me: Player = Depends(require_login)) -> ValhallaGame:
    """The winning side's account of the game, from one of the side that took it."""
    return _write_up(game, lambda: service.save_win_story(game, me.name, body.text))


def _write_up(game: str, write) -> ValhallaGame:
    """Both write-ups answer the same way: 404 for a game that is not in there, 403 for somebody
    it is not theirs to write, and the game itself once it is written."""
    try:
        write()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"{game} is not in Valhalla.")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return service.valhalla_game(game)


@router.get("/valhalla/{game}/replay")
def valhalla_replay(game: str, faction: str | None = None) -> GameReplay:
    """Every tick a finished game played, from one side or from all of them at once.

    Nobody has to be logged in and any side may be asked for: a game that is over has nobody left
    to keep anything from. See docs/gddr/0035-a-finished-game-is-watched-from-any-side.md."""
    try:
        return service.valhalla_replay(game, faction)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"{game} is not in Valhalla.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


@router.get("/solo")
def solo_game(me: Player = Depends(require_login)) -> SoloGame:
    """The caller's own game, if they have started one. Theirs alone: the name is not a path."""
    return service.solo_game(me.name)


@router.post("/solo")
def start_solo_game(body: SoloBody, me: Player = Depends(require_login)) -> SoloGame:
    """Start one, throwing away whatever they had. Played through the same routes as any game."""
    try:
        return service.start_solo_game(me.name, [s.model_dump() for s in body.ships])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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


@router.get("/{game}/replay")
def game_replay(game: str, faction: str | None = None, as_player: bool = False,
                me: Player = Depends(require_login)) -> GameReplay:
    """Every tick the game has played, for a playhead to scrub over.

    A commander gets their own side's game, whichever side they ask for of the ones they fly. Every
    side at once is more than anybody saw, so it is the director's.

    `as_player` is the director dropping to what one of their commanders sees, which is the same
    switch the game UI offers. It only ever narrows what is built, so it is safe to take from
    whoever asked."""
    if me.is_director and not as_player:
        return service.game_replay(game, faction)
    mine = service.player_factions(game, me.name)
    if not mine:
        raise HTTPException(status_code=403, detail=f"You fly nothing in {game}.")
    watching = faction if faction is not None else mine[0]
    if watching not in mine:
        raise HTTPException(status_code=403, detail=f"You do not fly for faction {watching}.")
    return service.game_replay(game, watching)


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