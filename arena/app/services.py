"""
Application-services layer: UI-agnostic operations over the game engine.

This is the "lower layer" that every UI's own facade sits on. It speaks in domain
terms and returns DTOs (see arena/app/dto.py). Storage -- currently pickle files behind
GameDirectory -- is an implementation detail hidden here and never exposed upward.

    GameService  -- player-facing, restricted operations (read state, plan moves).
    AdminService -- lower-level operations for the admin/director interface.
"""

import re
from pathlib import Path

from arena.cfg import GAME_DATA_DIR
from arena.engine.admin import GameSetup
from arena.engine.command import parse_commands
from arena.engine.game import Game
from arena.engine.gamedirectory import GameDirectory, ShipFile
from arena.engine.history import Tick
from arena.engine.objects.registry.builder import all_ship_types
from arena.engine.objects.starbase import Starbase
from arena.engine.objects.event import ExplosionEvent
from arena.app.players import DIRECTOR, LOGIN_COOKIE, Player, PlayerRegistry
from arena.app.dto import (
    GameSummary, ShipLimits, ScanInfo, TickState, ShipRound, CommandCheck,
    TrackPoint, TickEvent, ComponentStatus, Contact, ShipPlan, PlayerPlan, Explosion,
    WeaponInfo, WeaponInput,
    ShipSummary, FactionSummary, GameOverview, ShipTypeInfo, Me, LoginInfo,
)


class _EngineAccess:
    """Shared engine/storage access. The GameDirectory never leaves this layer."""

    def __init__(self, data_root: str = None):
        self.data_root = str(data_root if data_root is not None else GAME_DATA_DIR)
        self.players = PlayerRegistry(self.data_root)

    def _gd(self, game: str) -> GameDirectory:
        return GameDirectory(self.data_root, game)

    def _roster(self, game: str) -> dict[str, str]:
        """Which player commands which ship, from the game's ships file.

        The ships file rather than the saved rounds: it costs no unpickling, and it still lists a
        player whose every ship has been destroyed."""
        gd = self._gd(game)
        if not Path(gd.init_file).exists():
            return {}
        return {line.name: line.player for line in ShipFile(gd).ship_lines if line.player}

    def list_games(self) -> list[GameSummary]:
        summaries = []
        for d in sorted(Path(self.data_root).iterdir()):
            if d.is_dir():
                gd = GameDirectory(self.data_root, d.name)
                summaries.append(GameSummary(name=d.name, current_round=gd.last_round_number + 1))
        return summaries

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

    def me(self, player: Player) -> Me:
        return Me(name=player.name, is_director=player.is_director,
                  games=self.games_for_player(player.name))

    def ship_owner(self, game: str, ship: str) -> str | None:
        return self._roster(game).get(ship)

    # ---------------------------------------------------------------------- REFERENCE

    def list_ship_types(self) -> list[ShipTypeInfo]:
        """Every model in the registry. Reflection, so a new type needs no change here."""
        return [ShipTypeInfo(type_name=st.type_name, name=st.name,
                             category='Starbase' if issubclass(st.base_type, Starbase) else 'Ship',
                             specs=self._specs(st))
                for st in sorted(all_ship_types.values(), key=lambda t: t.name)]

    def list_ships(self, game: str) -> list[str]:
        return [s.name for s in Game(self._gd(game)).player_ships]

    def game_overview(self, game: str) -> GameOverview:
        """Every faction with its ships, who commands them and how they are scoring.

        Destroyed ships are included from the graveyard and marked, both because a score
        earned still counts and because their player can still review their history."""
        gd = self._gd(game)
        ois = gd.load_current_status()
        if ois is None:
            raise FileNotFoundError(f"{game} has no completed rounds yet")

        current_round = gd.last_round_number + 1
        by_faction: dict[str, list[ShipSummary]] = {}
        for pool, alive in ((ois, True), (gd.load_graveyard(), False)):
            for s in pool.values():
                if not getattr(s, 'is_player_controlled', False):
                    continue
                by_faction.setdefault(s.faction, []).append(ShipSummary(
                    name=s.name, ship_type=s._type.name,
                    player=getattr(s, 'player', None),   # an NPC ship has no player
                    score=s.score, alive=alive,
                    orders_in=gd.command_file_exists(s.name, current_round)))

        factions = [FactionSummary(name=f, score=sum(x.score for x in ships),
                                   ships=sorted(ships, key=lambda x: x.name))
                    for f, ships in by_faction.items()]
        # Best first, so the overview doubles as the scoreboard.
        factions.sort(key=lambda f: (-f.score, f.name))
        return GameOverview(name=game, last_round=gd.last_round_number, factions=factions)

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
        ois = gd.load_current_status()
        # Checked against every name the player could know, not only what is still in space,
        # so an order aimed at something already destroyed does not give that away.
        parse_result = parse_commands(lines, ois[ship_name], self._known_names(gd, ois, ois[ship_name]))
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
        """The faction-shared picture for a player, as at the end of a round.

        Returns the player's faction's ships in world coordinates (their own flagged), plus
        fog-of-war contacts: every non-faction object any faction ship scanned during that
        round, grouped per object into a chronological track of positions. Asking for an
        earlier round gives the picture as it was known then; only the latest round can
        still be planned.
        """
        gd = self._gd(game)
        last_round = gd.last_round_number
        if last_round < 0:
            raise FileNotFoundError(f"{game} has no completed rounds yet")
        if round_nr is None:
            round_nr = last_round
        if not 0 <= round_nr <= last_round:
            raise KeyError(f"{game} has no round {round_nr}")
        ois = gd.load_status(round_nr)
        # Every ship a player commands is theirs to plan, even in the unusual case of ships in
        # more than one faction. The graveyard is consulted too, so a player who has lost every
        # ship still has a faction and can look back over earlier rounds.
        factions = {s.faction for s in ois.values() if getattr(s, 'player', None) == player}
        if not factions:
            factions = {s.faction for s in gd.load_graveyard().values()
                        if getattr(s, 'player', None) == player}
        if not factions:
            raise KeyError(f"No ships for player '{player}' in {game}")

        faction_ships = [s for s in ois.values()
                         if getattr(s, 'is_player_controlled', False) and s.faction in factions]
        own_names = {s.name for s in faction_ships}
        round_ticks = Tick.for_start_of_round(round_nr).ticks_for_round

        ships = []
        for s in faction_ships:
            st = s._type
            # The state at the end of the round, taken from the history like everything else.
            final = s.history[round_ticks[-1]]
            pristine_weapons = {w.name: w for w in st.weapons}
            ships.append(ShipPlan(
                name=s.name, ship_type=st.name, category_name=s.category_name,
                x=s.pos.x, y=s.pos.y, heading=s.heading, speed=s.speed,
                hull=final['hull'], max_hull=st.max_hull,
                battery=final['battery'], max_battery=st.max_battery,
                owned=(getattr(s, 'player', None) == player),
                limits=ShipLimits(st.max_turn, st.max_delta_v, st.max_speed),
                components=self._component_status(s, final),
                specs=self._specs(st),
                weapons=[self._weapon_info(w, pristine_weapons[w.name])
                         for w in s.weapons.values()],
                track=[TrackPoint(tick=t.tick, x=s.history[t]['pos'].x, y=s.history[t]['pos'].y)
                       for t in round_ticks if t in s.history],
                events=[TickEvent(tick=t.tick, text=str(e), kind=e.kind)
                        for t in round_ticks if t in s.history
                        for e in s.history[t].non_scan_events],
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
                                'friendly': src.owner.faction in factions,
                                'pts': {},
                            }
                        acc['pts'].setdefault(t.tick, TrackPoint(tick=t.tick, x=scan.pos.x, y=scan.pos.y))
        contacts = [Contact(name=name, type_name=a['type_name'], category_name=a['category_name'],
                            friendly=a['friendly'], track=[a['pts'][k] for k in sorted(a['pts'])])
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

        return PlayerPlan(game=game, player=player, factions=sorted(factions), round=round_nr,
                          last_round=last_round, ships=ships, contacts=contacts,
                          explosions=list(blasts.values()))

    # ---------------------------------------------------------------- internals

    @staticmethod
    def _known_names(gd: GameDirectory, ois: dict, ship) -> dict:
        """The names a player may legitimately name as a target: whatever is in space now,
        the ships that have been destroyed, and everything this ship has ever scanned.

        Deliberately wider than what still exists. Validating against existence alone would
        reject an order aimed at something that has since been destroyed, and thereby tell
        the player it is gone; the shot is accepted here and simply fails when it is fired.
        Only validation uses this - the engine executes against the live objects, so a shot
        at something dead fizzles rather than hitting a corpse."""
        known = dict(ois)
        known.update(gd.load_graveyard())
        for tick_history in ship.history.ticks.values():
            for scan in tick_history.scans:
                known.setdefault(scan.name, scan.source)
        return known

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

    @staticmethod
    def _component_status(ship, snapshot: dict) -> list[ComponentStatus]:
        """Component state at the tick of that snapshot, with the type object's for comparison.

        Components with nothing to report are left out."""
        on_type = (ship._type.defense + ship._type.weapons + ship._type.ecm + ship._type.control)
        full = {c.name: {k: str(v) for k, v in c.status.items()} for c in on_type}
        return [ComponentStatus(name=name,
                                status={k: str(v) for k, v in status.items()},
                                full=full[name])
                for name, status in snapshot['components'].items() if status]

    @staticmethod
    def _weapon_info(weapon, pristine) -> WeaponInfo:
        """Describe a weapon well enough for an interface to offer the right controls.
        The inputs come from the weapon itself, so a new kind of weapon needs no changes here.
        `pristine` is the same weapon on the type object, which carries the full load."""
        inputs = []
        for p in weapon.expected_parameters:
            lo, hi = p.range if p.kind == 'number_in_range' else (None, None)
            inputs.append(WeaponInput(name=p.name, kind=p.kind, min=lo, max=hi))
        payload = weapon.payload_type
        return WeaponInfo(name=weapon.name, description=weapon.description,
                          firing_arc=weapon.firing_arc,
                          ammo=weapon.ammo, max_ammo=pristine.ammo,
                          payload=payload.name if payload else None,
                          payload_speed=(payload.max_speed or None) if payload else None,
                          inputs=inputs)

    @staticmethod
    def _load_ship(gd: GameDirectory, ship_name: str, round_nr: int):
        graveyard = gd.load_graveyard()
        if ship_name in graveyard:
            return graveyard[ship_name]
        return gd.load_status(round_nr)[ship_name]

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

    # ---------------------------------------------------------------------- LOGINS

    def logins(self) -> list[LoginInfo]:
        """Everyone who plays or could play: the registry, plus any player name a game knows
        that has no login yet. Those are the ones still owed a link."""
        registered = {p.name: p for p in self.players.all()}
        in_games = {name for g in self.list_games() for name in self._roster(g.name).values()}
        return [LoginInfo(name=name,
                          is_director=name in registered and registered[name].is_director,
                          token=registered[name].token if name in registered else '',
                          games=self.games_for_player(name))
                for name in sorted(registered.keys() | in_games)]

    def issue_login(self, name: str, director: bool = False) -> Player:
        """A fresh link for someone, replacing any they had."""
        return self.players.issue(name, role=DIRECTOR if director else '')

    def revoke_login(self, name: str) -> None:
        self.players.revoke(name)

    def create_game(self, name: str, ship_init_file: str) -> None:
        gd = GameDirectory(self.data_root, name)
        if not gd.exists or not gd.has_been_setup:
            GameSetup(gd, ShipFile(gd, ship_init_file)).execute()

    def process_turn(self, game: str) -> None:
        g = Game(self._gd(game))
        if g.current_round_ready:
            g.process_current_round()

    def command_status(self, game: str) -> dict[str, bool]:
        return Game(self._gd(game)).command_file_status