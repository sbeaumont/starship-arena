"""The seam every interface sits on: operations in domain terms, returning DTOs.

GameService is player-facing and restricted, AdminService is the director's. Storage stays below
this line. See docs/adr/0001-layered-architecture.md."""

import json
import logging
import random
import re
import shutil
from datetime import datetime
from math import atan2, degrees
from pathlib import Path

from arena.announce import Announcer
from arena.cfg import (ADMIN_UI_URL, COMMANDS_DIR, GAMES_ROOT, GamesRoot, INIT_FILE_NAME,
                       MANUAL_FILENAME, PLAY_URL, REGISTRATION_FILE_NAME, SCENARIO_FILE_NAME,
                       STATUS_FILE_TEMPLATE)
from arena.engine.admin import GameSetup, regenerate_game as engine_regenerate_game
from arena.engine.command import parse_commands
from arena.engine.game import Game
from arena.engine.gamedirectory import BodyFile, GameDirectory, ShipFile
from arena.engine.history import Tick
from arena.engine.objects.registry.builder import all_fielded_types
from arena.engine.objects.event import ExplosionEvent, HitEvent
from arena.engine.objects.objectinspace import Stance
from arena.engine.replay import Replay
from arena.app import scenarios
from arena.app.clock import next_occurrence, server_now, zone_name
from arena.app.naming import SOLO_PREFIX, for_display, is_solo_game_name, solo_game_name
from arena.app.players import DIRECTOR, LOGIN_COOKIE, PLAYER, Player, PlayerRegistry
from arena.app.registrations import Registration, RegistrationFile
from arena.app.dto import (
    FormingGame, GameSummary, OpenGame, ShipLimits, ScanInfo, TickState, ShipRound, CommandCheck,
    TrackPoint, TickEvent, TickCondition, ComponentStatus, Contact, ShipPlan, PlayerPlan, Explosion,
    Effect, GameReplay, ReplayObject, ObjectTick,
    WeaponInfo, ComponentInput,
    ShipSummary, FactionSummary, GameOverview, GameStanding, ShipTypeInfo, Me, LoginInfo,
    GameSettings, Pulse, GamePulse, JournalEntry, By, ProcessingTrigger, ServerTime, SoloGame,
)

logger = logging.getLogger('starship-arena.services')


def _entry(raw: dict) -> JournalEntry:
    return JournalEntry(at=raw['at'], event=raw['event'],
                        detail={k: str(v) for k, v in raw.items() if k not in ('at', 'event')})


class _EngineAccess:
    """Shared engine/storage access. The GameDirectory never leaves this layer."""

    def __init__(self, data_root: str | Path = None, announcer: Announcer = None):
        self.dirs = GamesRoot(Path(data_root)) if data_root is not None else GAMES_ROOT
        self.players = PlayerRegistry(self.dirs.root)
        self.announcer = announcer if announcer is not None else Announcer()

    def _gd(self, game: str) -> GameDirectory:
        """A game, wherever it is playable from: shared in `games/`, or somebody's own in `solo/`.

        Resolving it here is what lets one set of operations serve both, so nothing above this
        line asks which kind of game it is holding."""
        return GameDirectory(str(self.dirs.holding(game)), game)

    def _build_game(self, gd: GameDirectory, scenario, ships: list[dict]) -> None:
        """Deploy a roster over a scenario's terrain, and save the world that makes.

        Where a ship starts is the scenario's call, and it is written into the roster file, so a
        regenerate replays the deployment rather than drawing a new one."""
        placed = scenario.place(ships, random.Random())
        GameSetup(gd, ShipFile(gd, placed), BodyFile(gd, scenario.bodies())).execute()

    def _append_journal(self, game: str, event: str, **detail) -> None:
        """Add a line to the game's journal. Real time enters here, never below."""
        self._gd(game).append_journal({'at': server_now().isoformat(timespec='seconds'),
                                       'event': event, **detail})

    def _announce_round_processed(self, game: str, round_nr: int) -> None:
        """Tell the players a round is out, if this game is set to."""
        if self.settings(game).announce:
            self.announcer.announce(f"**{for_display(game)}** - round {round_nr} has been "
                                    f"processed. Plan your next one: {PLAY_URL}")

    def journal(self, game: str, limit: int = 0) -> list[JournalEntry]:
        """The game's journal, newest first, which is how a screen wants it."""
        return [_entry(raw) for raw in reversed(self._gd(game).read_journal(limit))]

    def list_games(self) -> list[GameSummary]:
        return self._games_in(self.dirs.games)

    def list_archived_games(self) -> list[GameSummary]:
        return self._games_in(self.dirs.archived)

    def list_registering_games(self) -> list[GameSummary]:
        return self._games_in(self.dirs.registering)

    def list_solo_games(self) -> list[GameSummary]:
        """Every player's own game. Not shown beside the shared ones anywhere."""
        return self._games_in(self.dirs.solo)

    def game_names_in_use(self) -> set[str]:
        """Played, archived, registering or somebody's own. All of them claim the name."""
        return {g.name for g in (self.list_games() + self.list_archived_games()
                                 + self.list_registering_games() + self.list_solo_games())}

    def scenario_of(self, game: str) -> str:
        return json.loads((self.dirs.registering / game / SCENARIO_FILE_NAME).read_text())['scenario']

    def registrations(self, game: str) -> list[Registration]:
        """Whoever registered, wherever the game is: still forming, or already started."""
        forming = self.dirs.registering / game
        return RegistrationFile(forming if forming.exists()
                                else self.dirs.games / game).all()

    def assign(self, game: str, factions: dict[str, str]) -> None:
        RegistrationFile(self.dirs.registering / game).assign(factions)

    def forming_games(self) -> list[FormingGame]:
        """Every game collecting registrations, with how much has come in."""
        forming = []
        for summary in self.list_registering_games():
            scenario = scenarios.by_key(self.scenario_of(summary.name))
            entries = self.registrations(summary.name)
            forming.append(FormingGame(name=summary.name, scenario=scenario.name,
                                       players=len(entries),
                                       ships=sum(e.ships for e in entries),
                                       assigned=sum(1 for e in entries if e.faction)))
        return forming

    def register(self, game: str, player: str, names: list[str]) -> Registration:
        scenario = scenarios.by_key(self.scenario_of(game))
        return RegistrationFile(self.dirs.registering / game).put(player, names, scenario.max_ships)

    def withdraw(self, game: str, player: str) -> None:
        RegistrationFile(self.dirs.registering / game).remove(player)

    @classmethod
    def _games_in(cls, root: Path) -> list[GameSummary]:
        if not root.exists():
            return []
        return [cls._summary_of(GameDirectory(str(root), d.name))
                for d in sorted(p for p in root.iterdir() if p.is_dir())]

    @classmethod
    def _summary_of(cls, gd: GameDirectory) -> GameSummary:
        hours = cls._settings_of(gd).process_hours
        due = next_occurrence(hours, server_now())
        return GameSummary(name=gd.game_name, current_round=gd.last_round_number + 1,
                           process_hours=hours,
                           next_processing=due.isoformat(timespec='seconds') if due else None,
                           standing=cls._standing_of(gd))

    def standing(self, game: str) -> GameStanding:
        return self._standing_of(self._gd(game))

    @staticmethod
    def _standing_of(gd: GameDirectory) -> GameStanding | None:
        """Who is owed what for the round being planned, or None while there is no round yet.

        Whether it can run is the engine's own verdict rather than something counted here, so
        there is only ever one definition of a round being ready to process."""
        if gd.last_round_number < 0:
            return None
        game = Game(gd)
        orders = game.command_file_status
        fleets: dict[str, list[str]] = {}
        for ship in game.player_ships:
            fleets.setdefault(ship.player, []).append(ship.name)
        return GameStanding(
            round_nr=game.current_round_nr,
            all_in=game.current_round_ready,
            ships=len(orders),
            orders_in=sum(1 for ok in orders.values() if ok),
            missing=sorted(name for name, ok in orders.items() if not ok),
            players=len(fleets),
            players_saved=sum(1 for names in fleets.values() if all(orders[n] for n in names)),
            players_ready=sum(1 for p in fleets if gd.is_ready(p, game.current_round_nr)))

    def _roster(self, game: str) -> dict[str, str]:
        """Which player commands which ship.

        The world rather than the ships file, because a ship the director spawned or a starbase
        replaced is in no roster. The world holds everything that exists and, keeping its own
        graveyard, everything that ever did."""
        return {s.name: s.player for s in Game(self._gd(game)).world.player_objects.values()}

    @staticmethod
    def _settings_of(gd: GameDirectory) -> GameSettings:
        raw = gd.read_settings()
        return GameSettings(on_all_ready=raw.get('process_on_all_ready', False),
                            process_hours=sorted(raw.get('process_hours', [])),
                            announce=raw.get('announce', True))

    def settings(self, game: str) -> GameSettings:
        return self._settings_of(self._gd(game))

    def save_settings(self, game: str, settings: GameSettings) -> None:
        hours = sorted(set(settings.process_hours))
        if any(not 0 <= h <= 23 for h in hours):
            raise ValueError(f"Hours run from 0 to 23: {hours}")
        self._gd(game).write_settings({'process_on_all_ready': settings.on_all_ready,
                                       'process_hours': hours,
                                       'announce': settings.announce})

    def all_ready(self, game: str) -> bool:
        players = {p for p in Game(self._gd(game)).players if p}
        return bool(players) and all(self.is_ready(game, p) for p in players)

    def is_ready(self, game: str, player: str) -> bool:
        """Whether a player has said they are done with the round being planned.

        Independent of whether orders are saved: you can save a plan and keep thinking."""
        gd = self._gd(game)
        return gd.is_ready(player, gd.last_round_number + 1)

    def set_ready(self, game: str, player: str, ready: bool) -> bool:
        """Returns whether saying so processed the round."""
        gd = self._gd(game)
        gd.set_ready(player, gd.last_round_number + 1, ready)
        if ready and self.settings(game).on_all_ready and self.all_ready(game):
            g = Game(self._gd(game))
            if g.current_round_ready:
                round_nr = g.current_round_nr
                g.process_current_round()
                self._append_journal(game, 'processed', round=round_nr,
                                     by=By.PLAYER, trigger=ProcessingTrigger.ALL_READY)
                self._announce_round_processed(game, round_nr)
                return True
        return False

    def pulse(self, game: str, player: str) -> Pulse:
        """Read from the ships file and the ready files only: no round is unpickled, because
        this is asked over and over while a player waits."""
        gd = self._gd(game)
        lines = [line for line in ShipFile(gd).ship_lines if line.player]
        factions = {line.faction for line in lines if line.player == player}
        players = {line.player for line in lines if line.faction in factions}
        round_nr = gd.last_round_number + 1
        return Pulse(last_round=gd.last_round_number,
                     ready={p: gd.is_ready(p, round_nr) for p in sorted(players)})

    def list_ship_types(self) -> list[ShipTypeInfo]:
        """Every model in the registry. Reflection, so a new type needs no change here."""
        return [ShipTypeInfo(type_name=st.type_name, name=st.name, category=st.category,
                             specs=self._specs(st))
                for st in sorted(all_fielded_types.values(), key=lambda t: t.name)]

    def game_overview(self, game: str) -> GameOverview:
        """Every faction with its ships, who commands them and how they are scoring.

        Destroyed ships are included from the graveyard and marked, both because a score
        earned still counts and because their player can still review their history."""
        gd = self._gd(game)
        world = gd.load_current_world()
        if world is None:
            raise FileNotFoundError(f"{game} has no completed rounds yet")

        current_round = gd.last_round_number + 1
        readiness: dict[str, bool] = {}
        by_faction: dict[str, list[ShipSummary]] = {}
        for pool, alive in ((world.objects, True), (world.graveyard, False)):
            for s in pool.values():
                if not s.is_player_controlled:
                    continue
                if s.player not in readiness:
                    readiness[s.player] = gd.is_ready(s.player, current_round)
                by_faction.setdefault(s.faction, []).append(ShipSummary(
                    name=s.name, ship_type=s._type.name, player=s.player,
                    score=s.score, alive=alive,
                    orders_in=gd.command_file_exists(s.name, current_round),
                    player_ready=readiness[s.player]))

        factions = [FactionSummary(name=f, score=sum(x.score for x in ships),
                                   ships=sorted(ships, key=lambda x: x.name))
                    for f, ships in by_faction.items()]
        # Best first, so the overview doubles as the scoreboard.
        factions.sort(key=lambda f: (-f.score, f.name))
        return GameOverview(name=game, last_round=gd.last_round_number, factions=factions)

    @staticmethod
    def _specs(ship_type) -> dict[str, str]:
        """What the type object says this model is. Each component describes itself."""
        specs = {
            'Hull': str(ship_type.max_hull),
            'Battery': f"{ship_type.start_battery}/{ship_type.max_battery}",
            'Generators': str(ship_type.generators),
            'Max speed': str(ship_type.max_speed),
            'Max turn': str(ship_type.max_turn),
            'Acceleration': str(ship_type.max_delta_v),
            'Scan range': str(ship_type.max_scan_distance),
        }
        for c in (ship_type.defense + ship_type.weapons + ship_type.ecm + ship_type.control):
            specs[c.name] = c.description
        return specs

    def games_for_player(self, name: str) -> list[str]:
        return [g.name for g in self.list_games() if name in self._roster(g.name).values()]


class GameService(_EngineAccess):
    """Player-facing operations: reading ship state and planning moves."""

    # ---------------------------------------------------------------------- WHO IS ASKING

    def resolve_login(self, token: str) -> Player | None:
        return self.players.by_token(token)

    def register_player(self, name: str) -> Player:
        """Claim a name nobody is using, and get a token for it.

        A name that already commands ships somewhere is not claimable: it belongs to whoever the
        director gave those ships to, and they get their link from the director."""
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name or ''):
            raise ValueError("A name starts with a letter and holds only letters, "
                             "numbers, dashes and underscores.")
        if self.players.by_name(name):
            raise ValueError(f"'{name}' is already registered.")
        if any(name in self._roster(g.name).values() for g in self.list_games()):
            raise ValueError(f"'{name}' already commands ships. Ask the director for a link.")
        return self.players.issue(name)

    @staticmethod
    def server_time() -> ServerTime:
        """The clock every processing hour is in. Open, like the hours themselves."""
        return ServerTime(now=server_now().isoformat(timespec='seconds'), zone=zone_name())

    def me(self, player: Player) -> Me:
        return Me(name=player.name, is_director=player.is_director,
                  games=self.games_for_player(player.name),
                  admin_url=ADMIN_UI_URL if player.is_director else '')

    def ship_owner(self, game: str, ship: str) -> str | None:
        return self._roster(game).get(ship)

    def open_games(self, player: str) -> list[OpenGame]:
        """Games taking registrations, with what this player has already asked for."""
        open_games = []
        for summary in self.list_registering_games():
            scenario = scenarios.by_key(self.scenario_of(summary.name))
            entries = self.registrations(summary.name)
            mine = next((e for e in entries if e.player == player), None)
            open_games.append(OpenGame(name=summary.name, scenario=scenario.name,
                                       blurb=scenario.blurb, max_ships=scenario.max_ships,
                                       players=len(entries), my_ships=mine.names if mine else []))
        return open_games

    # ---------------------------------------------------------------------- A GAME OF THEIR OWN

    def solo_game(self, player: str) -> SoloGame:
        """The one game this player may run on their own, started or not."""
        gd = GameDirectory(str(self.dirs.solo), solo_game_name(player))
        return SoloGame(scenario=scenarios.SOLO.name, blurb=scenarios.SOLO.blurb,
                        max_ships=scenarios.SOLO.max_ships,
                        game=self._summary_of(gd) if gd.exists else None)

    def start_solo_game(self, player: str, picks: list[dict]) -> SoloGame:
        """Build this player's own game from the hulls they picked, throwing away the one they had.

        It runs a round the moment they say they are ready, because they are the only one it
        waits for, and it announces nothing: a practice round is nobody else's news."""
        scenario = scenarios.SOLO
        name = solo_game_name(player)
        ships = scenario.roster(player, picks, random.Random())
        self.dirs.solo.mkdir(parents=True, exist_ok=True)
        theirs = self.dirs.solo / name
        if theirs.exists():
            shutil.rmtree(theirs)
        self._build_game(GameDirectory(str(self.dirs.solo), name), scenario, ships)
        self.save_settings(name, GameSettings(on_all_ready=True, process_hours=[], announce=False))
        return self.solo_game(player)

    # ---------------------------------------------------------------------- REFERENCE

    def manual(self) -> bytes:
        """The manual as the CLI last built it. Bytes, so no interface learns where it is kept."""
        return Path(MANUAL_FILENAME).read_bytes()

    def list_ships(self, game: str) -> list[str]:
        return [s.name for s in Game(self._gd(game)).player_ships]

    def get_ship_round(self, game: str, ship_name: str, round_nr: int) -> ShipRound:
        gd = self._gd(game)
        ship = self._load_ship(gd, ship_name, round_nr)
        start_tick = Tick.for_start_of_round(round_nr)
        start = self._tick_state(ship, start_tick.prev_round_end)
        ticks = [ts for t in start_tick.ticks_for_round if (ts := self._tick_state(ship, t))]
        st = ship._type
        limits = ShipLimits(max_turn=st.max_turn, max_delta_v=st.max_delta_v, max_speed=st.max_speed)
        return ShipRound(game=game, ship=ship.name, ship_type=st.name, round=round_nr,
                         start=start, ticks=ticks, limits=limits)

    def get_commands(self, game: str, ship_name: str, round_nr: int = None) -> list[str]:
        """The orders for a round; by default the one being planned now."""
        gd = self._gd(game)
        if round_nr is None:
            round_nr = gd.last_round_number + 1
        if gd.command_file_exists(ship_name, round_nr):
            return gd.read_command_file(ship_name, round_nr)
        return []

    def check_commands(self, game: str, ship_name: str, lines: list[str]) -> list[CommandCheck]:
        gd = self._gd(game)
        world = gd.load_current_world()
        parse_result = parse_commands(lines, world.objects[ship_name], world)
        checks = []
        for tick in sorted(parse_result.keys()):
            for c in parse_result[tick].all:
                checks.append(CommandCheck(line=c.command_line.text, ok=c.is_valid, feedback=c.feedback_results))
        return checks

    def save_commands(self, game: str, ship_name: str, lines: list[str]) -> None:
        gd = self._gd(game)
        round_nr = gd.last_round_number + 1
        with open(gd.command_file(ship_name, round_nr), 'w') as f:
            f.write('\n'.join(lines))

    def get_player_plan(self, game: str, player: str, round_nr: int = None) -> PlayerPlan:
        """The faction-shared picture for a player at the end of a round.

        Their faction's ships in world coordinates, plus fog-of-war contacts: everything any
        faction ship scanned, as a track of sightings. An earlier round gives the picture as it
        was known then."""
        gd = self._gd(game)
        last_round = gd.last_round_number
        if last_round < 0:
            raise FileNotFoundError(f"{game} has no completed rounds yet")
        if round_nr is None:
            round_nr = last_round
        if not 0 <= round_nr <= last_round:
            raise KeyError(f"{game} has no round {round_nr}")
        world = gd.load_world(round_nr)
        ois = world.objects
        factions = self._factions_of(world, player)
        if not factions:
            raise KeyError(f"No ships for player '{player}' in {game}")

        round_ticks = Tick.for_start_of_round(round_nr).ticks_for_round
        faction_ships = [s for s in ois.values()
                         if s.is_player_controlled and s.faction in factions]
        alive_names = {s.name for s in faction_ships}
        # A ship destroyed during this round is gone from the saved state but its history is in
        # the graveyard, and its player should be able to read what happened to it.
        faction_ships += [s for s in world.graveyard.values()
                          if s.faction in factions and s.name not in alive_names
                          and round_ticks[0] in s.history]
        own_names = {s.name for s in faction_ships}
        readiness = {p: gd.is_ready(p, last_round + 1)
                     for p in {s.player for s in faction_ships} if p}

        ships = []
        for s in faction_ships:
            st = s._type
            recorded = [t for t in round_ticks if t in s.history]
            final = s.history[recorded[-1]]
            pristine_weapons = {w.name: w for w in st.weapons}
            ships.append(ShipPlan(
                name=s.name, ship_type=st.name, category_name=s.category_name,
                x=s.pos.x, y=s.pos.y, heading=s.heading, speed=s.speed,
                hull=round(final['hull'], 1), max_hull=st.max_hull,
                battery=round(final['battery'], 1), max_battery=st.max_battery,
                player=s.player,
                player_ready=readiness.get(s.player, False),
                owned=(s.player == player),
                limits=ShipLimits(st.max_turn, st.max_delta_v, st.max_speed),
                scan_range=st.max_scan_distance,
                components=self._component_status(s, final, world),
                specs=self._specs(st),
                weapons=[self._weapon_info(w, pristine_weapons[w.name], world)
                         for w in s.weapons.values()],
                track=[TrackPoint(tick=t.tick, x=s.history[t]['pos'].x, y=s.history[t]['pos'].y)
                       for t in recorded],
                events=[TickEvent(tick=t.tick, abs_tick=t.abs_tick, text=str(e), kind=e.kind)
                        for t in recorded for e in s.history[t].non_scan_events],
                conditions=[self._tick_condition(s, t) for t in recorded],
                alive=s.name in alive_names,
                # Orders are planned from the end of a round, so they belong to the one after
                # it. For the last round that is the current round, still open for changes.
                commands=self.get_commands(game, s.name, round_nr + 1),
            ))

        seen: dict[str, dict] = {}
        for s in faction_ships:
            for t in round_ticks:
                if t in s.history:
                    for scan in s.history[t].scans:
                        if scan.name in own_names:
                            continue  # allies are ground truth, not fog-of-war contacts
                        acc = seen.get(scan.name)
                        if acc is None:
                            src = scan.source
                            acc = seen[scan.name] = {
                                'type_name': src.type_name,
                                'category_name': src.category_name,
                                'stance': self._stance(src, factions),
                                'radius': src.radius,
                                'pts': {},
                            }
                        acc['pts'].setdefault(t.tick, TrackPoint(tick=t.tick, x=scan.pos.x, y=scan.pos.y))
        contacts = [Contact(name=name, type_name=a['type_name'], category_name=a['category_name'],
                            stance=a['stance'], radius=a['radius'],
                            track=[a['pts'][k] for k in sorted(a['pts'])])
                    for name, a in seen.items()]

        # Explosions the faction witnessed. The engine hands an ExplosionEvent to every
        # object close enough to scan it, so a ship's history already holds exactly the
        # blasts it saw. The same blast is seen by several ships, hence the dedup.
        blasts: dict[tuple, Explosion] = {}
        for s in faction_ships:
            for t in round_ticks:
                if t in s.history:
                    for e in s.history[t].events:
                        if isinstance(e, ExplosionEvent):
                            key = (t.tick, e.pos.x, e.pos.y, e.radius)
                            blasts.setdefault(key, Explosion(tick=t.tick, x=e.pos.x, y=e.pos.y,
                                                             radius=e.radius, damage_type=str(e._type)))

        # What the faction's own blows did. Read off the striker's history, and placed from what
        # the target was doing on that tick: you hit it, so where it was is not fog of war. A
        # faction mate who watched the same hit holds the same event, hence the dedup.
        landed: dict[tuple, Effect] = {}
        for s in faction_ships:
            for t in round_ticks:
                if t in s.history:
                    for e in s.history[t].events:
                        if not (isinstance(e, HitEvent) and e.source.owner.name in own_names):
                            continue
                        struck = self._where_at(world, e.target.name, t)
                        striker = self._where_at(world, e.source.owner.name, t)
                        if struck is None or striker is None:
                            continue
                        for x in e.effects:
                            landed.setdefault(
                                (t.tick, e.target.name, x.part, str(x.outcome)),
                                Effect(tick=t.tick, x=struck.x, y=struck.y,
                                       bearing=round(degrees(atan2(striker.x - struck.x,
                                                                   striker.y - struck.y)) % 360, 1),
                                       target=e.target.name, part=x.part,
                                       outcome=str(x.outcome), amount=x.amount, points=x.points))

        return PlayerPlan(game=game, player=player, factions=sorted(factions), round=round_nr,
                          last_round=last_round, ready=gd.is_ready(player, last_round + 1),
                          ships=ships, contacts=contacts, explosions=list(blasts.values()),
                          effects=list(landed.values()))

    def player_factions(self, game: str, player: str) -> list[str]:
        """Which sides a commander flies in a game. Empty for anyone who flies nothing in it."""
        return sorted(self._factions_of(self._gd(game).load_current_world(), player))

    def game_replay(self, game: str, faction: str = None) -> GameReplay:
        """Every tick the game has played, per object: where it was and what happened to it.

        One side's war when a faction is named: its own objects as they were, and everything else
        only where its ships saw it, so what it never saw is not built and cannot be read out of
        what was sent. Without one this is every side at once.

        One pass over the ticks, because which world knows about a tick is the replay's business
        and not this one's."""
        replay = Replay(self._gd(game))
        objects: dict[str, ReplayObject] = {}
        for tick in replay.ticks:
            in_space = replay.objects_at(tick)
            mine = {name: ois for name, ois in in_space.items()
                    if faction is None or self._side_of(ois) == faction}
            for name, ois in mine.items():
                snapshot = ois.history[tick]
                self._recorded(objects, ois, contact=False).path.append(
                    ObjectTick(abs_tick=tick.abs_tick, x=snapshot['pos'].x, y=snapshot['pos'].y,
                               heading=snapshot['heading'], speed=snapshot['speed']))
                objects[name].events.extend(
                    TickEvent(tick=tick.tick, abs_tick=tick.abs_tick, text=str(e), kind=e.kind)
                    for e in snapshot.non_scan_events)
            if faction is None:
                continue
            # What the side saw of everything else, off the ships whose scans a faction shares.
            # Several of them see the same object, so a tick gets one point however many looked.
            for ois in [o for o in mine.values() if o.is_player_controlled]:
                for scan in ois.history[tick].scans:
                    if scan.name in mine:
                        continue
                    seen = self._recorded(objects, scan.source, contact=True)
                    if not seen.path or seen.path[-1].abs_tick != tick.abs_tick:
                        seen.path.append(ObjectTick(abs_tick=tick.abs_tick, x=scan.pos.x,
                                                    y=scan.pos.y, heading=None, speed=None))
        return GameReplay(game=game, faction=faction,
                          first_tick=replay.first.abs_tick, last_tick=replay.last.abs_tick,
                          objects=list(objects.values()))

    def _recorded(self, objects: dict, ois, contact: bool) -> ReplayObject:
        """The row this object is building up in a replay, opened the first time it turns up."""
        if ois.name not in objects:
            objects[ois.name] = ReplayObject(
                name=ois.name, type_name=ois.type_name, category_name=ois.category_name,
                faction=self._side_of(ois), owner=ois.owner.name if ois.owner else None,
                radius=ois.radius, contact=contact, path=[], events=[])
        return objects[ois.name]

    @staticmethod
    def _where_at(world, name: str, tick: Tick):
        """Where something was at the end of a tick, from its own snapshot. The graveyard counts:
        the thing you killed stopped existing, and where it died is the interesting part."""
        obj = world.objects.get(name) or world.graveyard.get(name)
        return obj.history[tick]['pos'] if obj and tick in obj.history else None

    # ---------------------------------------------------------------- internals


    @staticmethod
    def _factions_of(world, player: str) -> set:
        """Which sides a commander flies, in the unusual case of ships in more than one.

        The graveyard answers when nothing of theirs is left in space, so losing every ship does
        not take a player's side away and they can still look back over the game."""
        for where in (world.objects, world.graveyard):
            flown = {s.faction for s in where.values()
                     if s.is_player_controlled and s.player == player}
            if flown:
                return flown
        return set()

    @staticmethod
    def _side_of(ois) -> str | None:
        """Which side something is on. Ordnance carries no faction of its own and reaches one
        through its owner, which is how anything a ship puts into space knows whose side it is on.
        Terrain is on nobody's."""
        return ois.faction or (ois.owner.faction if ois.owner else None)

    @staticmethod
    def _stance(src, factions: set) -> str:
        """How a contact stands to the fleet being planned for.

        The engine answers this between two objects; here it is against every faction a player is
        flying, so the three cases are spelled out once rather than at each reader."""
        if not src.owner.faction:
            return str(Stance.Neutral)
        return str(Stance.Friend if src.owner.faction in factions else Stance.Foe)

    @staticmethod
    def _tick_condition(ship, tick) -> TickCondition:
        """Shields come from whichever component the type calls its defence, so nothing here
        needs to know what a shield is called."""
        snap = ship.history[tick]
        defence = next((c.name for c in ship._type.defense), None)
        return TickCondition(tick=tick.tick, hull=round(snap['hull'], 1),
                             battery=round(snap['battery'], 1),
                             shields={k: str(v) for k, v in
                                      snap['components'].get(defence, {}).items()})

    def _component_status(self, ship, snapshot: dict, world) -> list[ComponentStatus]:
        """Component state at the tick of that snapshot, with the type object's for comparison.

        Components with nothing to report are left out. The inputs come off the live component,
        since a cloak's ceiling and a shield's headroom are answered from the ship it is on."""
        st = ship._type
        collections = {'defense': st.defense, 'weapons': st.weapons,
                       'ecm': st.ecm, 'control': st.control}
        pristine = {c.name: (group, c) for group, comps in collections.items() for c in comps}
        return [ComponentStatus(name=name, group=pristine[name][0],
                                status={k: str(v) for k, v in status.items()},
                                full={k: str(v) for k, v in pristine[name][1].status.items()},
                                inputs=self._inputs(ship.all_components[name], world))
                for name, status in snapshot['components'].items() if status]

    @staticmethod
    def _inputs(component, world) -> list[ComponentInput]:
        """What an order to this component needs, as controls an interface can offer."""
        inputs = []
        for p in component.expected_parameters:
            if p.needs_world:
                p.set_world(world)
            lo, hi = p.range if p.kind == 'number_in_range' else (None, None)
            inputs.append(ComponentInput(name=p.name, kind=p.kind, min=lo, max=hi,
                                         choices=p.choices))
        return inputs

    def _weapon_info(self, weapon, pristine, world) -> WeaponInfo:
        """What the map needs to draw this weapon's shot, beyond what its component row says.
        `pristine` is the same weapon on the type object, which carries the full load."""
        payload = weapon.payload_type
        return WeaponInfo(name=weapon.name, description=weapon.description,
                          firing_arc=weapon.firing_arc,
                          ammo=weapon.ammo, max_ammo=pristine.ammo,
                          payload=payload.name if payload else None,
                          payload_speed=(payload.max_speed or None) if payload else None,
                          inputs=self._inputs(weapon, world))

    @staticmethod
    def _load_ship(gd: GameDirectory, ship_name: str, round_nr: int):
        world = gd.load_world(round_nr)
        if ship_name in world.graveyard:
            return world.graveyard[ship_name]
        return world.objects[ship_name]

    def _tick_state(self, ship, tick: Tick) -> TickState | None:
        if tick not in ship.history:
            return None
        th = ship.history[tick]
        pos = th['pos']
        return TickState(
            tick=tick.tick,
            x=pos.x, y=pos.y,
            heading=th['heading'], speed=th['speed'],
            events=[str(e) for e in th.non_scan_events],
            scans=[self._scan_info(s, ship) for s in th.scans],
        )

    @staticmethod
    def _scan_info(scan, ship) -> ScanInfo:
        return ScanInfo(
            name=scan.name, x=scan.pos.x, y=scan.pos.y,
            distance=scan.distance, direction=scan.direction, heading=scan.heading,
            friendly=(scan.source.faction == ship.faction),
        )


class AdminService(_EngineAccess):
    """Lower-level operations for the admin/director interface."""

    def process_due(self) -> list[str]:
        """Force a round in every game whose settings say this hour is its hour.

        Called once an hour by cron, which is where the timing comes from: the games say which
        hour they want, and nothing here measures elapsed time. Deadlines override readiness, so a
        due game processes whether the orders are in or not."""
        now = server_now()
        run = []
        for game in self.list_games():
            try:
                if now.hour not in self.settings(game.name).process_hours:
                    continue
                if self._deadline_already_fired(game.name, now):
                    run.append(f"{game.name}: this hour's deadline has already run")
                    continue
                logger.info(f"{game.name}: processing round {game.current_round}")
                silent = self.force_process_turn(game.name, By.CRON, ProcessingTrigger.DEADLINE)
                run.append(f"{game.name}: round {game.current_round} processed"
                           + (f", no orders from {', '.join(silent)}" if silent else ""))
            except Exception as e:
                # One unreadable game must not stop the rest of the hour's work.
                run.append(f"{game.name}: FAILED, {e}")
                self._append_journal(game.name, 'failed', round=game.current_round,
                                     by=By.CRON, trigger=ProcessingTrigger.DEADLINE, error=str(e))
        return run

    def _deadline_already_fired(self, game: str, now: datetime) -> bool:
        """Whether this game's deadline has already run this hour. Nothing else is asked."""
        for raw in reversed(self._gd(game).read_journal()):
            at = datetime.fromisoformat(raw['at'])
            if (at.date(), at.hour) != (now.date(), now.hour):
                return False
            if raw.get('trigger') == ProcessingTrigger.DEADLINE:
                return True
        return False

    # ---------------------------------------------------------------------- GAMES

    def archive_game(self, name: str) -> None:
        """Move a game out of every list. Its data is untouched."""
        self.dirs.archived.mkdir(parents=True, exist_ok=True)
        target = self.dirs.archived / name
        if target.exists():
            raise ValueError(f"'{name}' is already archived.")
        shutil.move(str(self.dirs.games / name), str(target))

    def unarchive_game(self, name: str) -> None:
        self.dirs.games.mkdir(parents=True, exist_ok=True)
        target = self.dirs.games / name
        if target.exists():
            raise ValueError(f"A game called '{name}' is already being played.")
        shutil.move(str(self.dirs.archived / name), str(target))

    def delete_archived_game(self, name: str) -> None:
        """Delete for good. Only reaches into the archive, so a live game cannot be lost here."""
        shutil.rmtree(self.dirs.archived / name)

    # ---------------------------------------------------------------------- LOGINS

    def logins(self) -> list[LoginInfo]:
        """Everyone in the registry. A game's rosters are not consulted: a name is on this list
        because somebody put it here, so removing it removes it."""
        return [LoginInfo(name=p.name, is_director=p.is_director, token=p.token,
                          games=self.games_for_player(p.name), active=p.active)
                for p in sorted(self.players.all(), key=lambda p: p.name)]

    def issue_login(self, name: str, director: bool = False) -> Player:
        """A fresh link for someone, replacing any they had."""
        return self.players.issue(name, role=DIRECTOR if director else PLAYER)

    def reissue_login(self, name: str) -> Player:
        """A fresh link for someone already listed, keeping the role they have."""
        had = self.players.by_name(name)
        return self.players.issue(name, role=had.role if had else PLAYER)

    def remove_login(self, name: str) -> None:
        self.players.remove_link(name)

    def remove_player(self, name: str) -> None:
        self.players.remove(name)

    def set_player_active(self, name: str, active: bool) -> None:
        self.players.set_active(name, active)

    def _claim_name(self, name: str) -> None:
        """Refuse a name a shared game may not take. Every way of naming one comes through here.

        Solo names are reserved as a set rather than one at a time: player names are unique, so
        the prefix speaks for all of them whether or not anybody has started one. Nothing then has
        to be disambiguated later, and where a game directory sits still says what kind it is."""
        if is_solo_game_name(name):
            raise ValueError(f"'{name}' is reserved: a name starting with '{SOLO_PREFIX}' "
                             f"belongs to a player's own game.")
        if name in self.game_names_in_use():
            raise ValueError(f"A game called '{name}' already exists.")

    def create_game(self, name: str, ships: list[dict], scenario: str) -> None:
        """Name a game and build it: its roster deployed, its terrain in place."""
        self._claim_name(name)
        self.dirs.games.mkdir(parents=True, exist_ok=True)
        self._build_game(GameDirectory(str(self.dirs.games), name),
                         scenarios.by_key(scenario), ships)

    # ---------------------------------------------------------------------- BEFORE IT STARTS

    def open_registrations(self, name: str, scenario: str) -> None:
        """Name a game and start collecting registrations for it."""
        scenarios.by_key(scenario)
        self._claim_name(name)
        target = self.dirs.registering / name
        target.mkdir(parents=True)
        (target / SCENARIO_FILE_NAME).write_text(json.dumps({'scenario': scenario}) + '\n')

    def is_reopenable(self, name: str) -> bool:
        """Built from registrations and no round played yet, so the roster can still be redealt."""
        gd = GameDirectory(str(self.dirs.games), name)
        return (gd.last_round_number <= 0
                and (self.dirs.games / name / REGISTRATION_FILE_NAME).exists())

    def reopen_registrations(self, name: str) -> None:
        """Put a started game back into registration, roster and all.

        Only before its first round: after that the roster is what people have been playing."""
        source = self.dirs.games / name
        gd = GameDirectory(str(self.dirs.games), name)
        if gd.last_round_number > 0:
            raise ValueError(f"'{name}' has played rounds. Archive it instead.")
        if not (source / REGISTRATION_FILE_NAME).exists():
            raise ValueError(f"'{name}' was not built from registrations.")
        for leftover in (INIT_FILE_NAME, STATUS_FILE_TEMPLATE.format(0)):
            (source / leftover).unlink(missing_ok=True)
        shutil.rmtree(source / COMMANDS_DIR, ignore_errors=True)
        self.dirs.registering.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(self.dirs.registering / name))

    def start_game(self, name: str, ships: list[dict], settings: GameSettings) -> None:
        """Move the directory into play, write the roster, keep the registrations as the record."""
        self.dirs.games.mkdir(parents=True, exist_ok=True)
        target = self.dirs.games / name
        if target.exists():
            raise ValueError(f"A game called '{name}' is already being played.")
        # Asked before the move, because the scenario is read from where the game is registering.
        scenario = self.scenario_of(name)
        shutil.move(str(self.dirs.registering / name), str(target))
        # The name was claimed when registrations opened, and the directory is already here.
        self._build_game(GameDirectory(str(self.dirs.games), name),
                         scenarios.by_key(scenario), ships)
        self.save_settings(name, settings)

    def spawn_ship(self, game: str, name: str, ship_type: str, player: str = '',
                   faction: str = None, x: int = 0, y: int = 0, heading: int = 0,
                   round_nr: int = None, tick: int = 1) -> None:
        """Schedule a ship for the start of a round, this one or a later one.

        Tick 1 by default, so a director's reinforcement is there for the whole round rather than
        appearing in the middle of a fight. Arriving part way through is what a scenario trigger
        is for. Written to the spawn plan rather than into the world, because the world is derived
        and a regenerate would otherwise lose it."""
        gd = self._gd(game)
        g = Game(gd)
        round_nr = g.current_round_nr if round_nr is None else round_nr
        if round_nr < g.current_round_nr:
            raise ValueError(f"Round {round_nr} has been played. The earliest is {g.current_round_nr}.")
        if name in g.world.all_names:
            raise ValueError(f"'{name}' has been used in this game already.")
        if ship_type not in all_fielded_types:
            raise ValueError(f"'{ship_type}' is not a known ship type.")
        if player and not self.players.by_name(player):
            raise ValueError(f"'{player}' has no login. Issue one first.")
        record = {'round': round_nr, 'tick': tick, 'name': name, 'type': ship_type,
                  'x': x, 'y': y, 'heading': heading}
        if player:
            record['player'] = player
        if faction:
            record['faction'] = faction
        gd.append_spawn(record)

    def process_turn(self, game: str) -> bool:
        """Process only when every order is in. Returns whether it ran."""
        g = Game(self._gd(game))
        if not g.current_round_ready:
            return False
        round_nr = g.current_round_nr
        g.process_current_round()
        self._append_journal(game, 'processed', round=round_nr,
                             by=By.DIRECTOR, trigger=ProcessingTrigger.MANUAL)
        self._announce_round_processed(game, round_nr)
        return True

    def force_process_turn(self, game: str, by: By, trigger: ProcessingTrigger) -> list[str]:
        """Process whether or not the orders are in, writing an empty file for those that are not.

        An empty command file reads as "no orders arrived in time", which is what a deadline
        means. Returns the ships it had to do that for."""
        gd = self._gd(game)
        g = Game(gd)
        round_nr = g.current_round_nr
        silent = sorted(g.missing_command_files)
        for ship in silent:
            with open(gd.command_file(ship, round_nr), 'w') as f:
                f.write('')
        Game(gd).process_current_round()
        detail = {'round': round_nr, 'by': by, 'trigger': trigger}
        if silent:
            detail['no_orders_from'] = ', '.join(silent)
        self._append_journal(game, 'processed', **detail)
        self._announce_round_processed(game, round_nr)
        return silent

    def regenerate_game(self, game: str) -> int:
        """Replay from the plans, back to the round it was on. Returns the round it ended on."""
        to_round = engine_regenerate_game(self._gd(game))
        self._append_journal(game, 'regenerated', round=to_round, by=By.DIRECTOR)
        return to_round

    def command_status(self, game: str) -> dict[str, bool]:
        return Game(self._gd(game)).command_file_status

    def game_pulse(self, game: str) -> GamePulse:
        """Polled by the console: read from the ships file and the ready files, no round loaded.

        It answers for every ship the game was set up with, including the dead."""
        gd = self._gd(game)
        roster = self._roster(game)
        round_nr = gd.last_round_number + 1
        return GamePulse(round_nr=round_nr,
                         orders={ship: gd.command_file_exists(ship, round_nr) for ship in roster},
                         ready={p: gd.is_ready(p, round_nr) for p in sorted(set(roster.values()))})