"""
Administrative features
- setting up a new game.
"""

from collections import defaultdict
import logging

import arena.engine.objects.registry.builder as builder
from arena.engine.gamedirectory import BodyFile, GameDirectory, ShipFile
from arena.engine.world import World
from arena.engine.game import Game
from arena.engine.history import TICK_ZERO

logger = logging.getLogger('starship-arena.admin')


def group_by_faction(ships) -> dict:
    result = defaultdict(list)
    for s in ships:
        result[s.faction].append(s)
    return result


class GameSetup(object):
    def __init__(self, game_directory: GameDirectory, ship_file: ShipFile=None,
                 body_file: BodyFile=None):
        self._dir: GameDirectory = game_directory
        self.shipfile = ship_file if ship_file else ShipFile(self._dir)
        self.bodyfile = body_file if body_file else BodyFile(self._dir)
        self.ships: dict = self._init_ships(self.shipfile.ship_lines)
        self.bodies: dict = self._init_bodies(self.bodyfile.body_lines)
        self.world = World(self._dir, self.ships | self.bodies)

    def execute(self):
        self._dir.setup_directories()
        self._dir.clean()
        self.run_tick_zero()
        for faction, ships in group_by_faction(self.ships.values()).items():
            logger.info(f"=={faction}==")
            for ship in ships:
                logger.info(f"Ship: {ship.name}, Faction: {ship.faction}, Pos: {ship.pos}, Type: {ship.class_name}")
        self.save()

    def run_tick_zero(self):
        for ois in self.world.objects.values():
            ois.history.set_tick(TICK_ZERO)
            ois.scan(self.world)
            ois.history.update()

    def _init_bodies(self, body_file: list) -> dict:
        """Terrain, placed exactly where it was written. Nothing scatters a body."""
        bodies = dict()
        for line in body_file:
            body = builder.create(line.name, line.type, line.xy)
            bodies[body.name] = body
        return bodies

    def _init_ships(self, ship_file: list) -> dict:
        """Load and initialize all the ships to their status at the start of a round.

        Where a ship starts and which way it looks are the roster's to say: a scenario deployed it
        before the file was ever written. Nothing here moves anything."""
        objects_in_space = dict()
        for line in ship_file:
            ois = builder.create(line.name, line.type, line.xy, line.heading, player=line.player)
            ois.faction = line.faction
            objects_in_space[ois.name] = ois
        return objects_in_space

    def save(self):
        """Save the round 0 pickle file and the ships file with coordinates (to ensure idempotency)."""
        self.world.save(0)
        self.shipfile.save(self.ships.values())
        if self.bodyfile.body_lines:
            self.bodyfile.save()


def regenerate_game(gd: GameDirectory) -> int:
    """Rebuild a game from its ships file and command files, back to the round it was on.

    Snapshots are written as rounds are processed, so a change to what they hold only reaches
    rounds processed afterwards; this replays the earlier ones. Deterministic, because the ships
    file holds where everything started and setup draws nothing. Returns the round it ended on."""
    target = gd.last_round_number
    logger.info(f"Regenerating {gd.game_name} up to round {target}")
    GameSetup(gd).execute()
    while gd.last_round_number < target:
        game = Game(gd)
        if not game.current_round_ready:
            logger.info(f"Stopping at round {gd.last_round_number}: not all orders are in")
            break
        game.process_current_round()
    return gd.last_round_number


def setup_game(gd: GameDirectory, ship_file: ShipFile=None) -> Game:
    setup = GameSetup(gd, ship_file)
    logger.info(f"Setup {gd.path} for ship file: {setup.shipfile}")
    setup.execute()
    logger.info(f"Current status: {gd.load_current_world().objects}")
    return Game(gd)
