"""
Administrative features
- setting up a new game.
"""

from collections import defaultdict
from math import cos, sin, radians
from random import randint
import logging

import arena.engine.objects.registry.builder as builder
from arena.engine.gamedirectory import GameDirectory, ShipFile
from arena.engine.game import Game
from arena.engine.objects.objectinspace import Point
from arena.engine.reporting.visualize import Visualizer
from arena.engine.reporting.report import report_round_zero
from arena.engine.history import TICK_ZERO

logger = logging.getLogger('starship-arena.admin')


def polar_to_cartesian(r, theta) -> (int, int):
    """theta in degrees

    returns tuple; (int, int); (x, y)
    """
    x = r * cos(radians(theta))
    y = r * sin(radians(theta))
    return round(x), round(y)


def centers_for(num_factions, distance, random_rotation=60, angle_tweak=(0, 0), distance_tweak=(0, 0)) -> list[(int, int)]:
    result = list()
    rotation = randint(0, random_rotation)
    for i in range(num_factions):
        angle = (i * int(360 / num_factions)) + rotation
        tweaked_angle = angle + randint(*angle_tweak)
        tweaked_distance = distance + randint(*distance_tweak)
        result.append(polar_to_cartesian(tweaked_distance, tweaked_angle))
    return result


def group_by_faction(ships) -> dict:
    result = defaultdict(list)
    for s in ships:
        result[s.faction].append(s)
    return result


def visualise_points(list_of_points):
    boundaries = Visualizer.boundaries(list_of_points, padding=50)
    vis = Visualizer(boundaries, scale=2)
    vis.draw_circle(Point(0, 0))
    for p in list_of_points:
        vis.draw_circle(Point(*p))
    vis.show()


def distribute_factions(ships, distance) -> None:
    """Distribute the factions evenly along a circle centered around (0, 0) and radius of distance"""
    factions = {s.faction for s in ships}
    faction_centers = centers_for(len(factions), distance, angle_tweak=(-10, 10), distance_tweak=(-30, 60))
    faction_groups = group_by_faction(ships)
    for center, group in zip(faction_centers, faction_groups.values()):
        num_ships_in_faction = len(group)
        offsets = centers_for(num_ships_in_faction, 20, angle_tweak=(-30, 30), distance_tweak=(0, 30))
        for ship, offset in zip(group, offsets):
            # Only move ship if it has not already been set in the ships file
            if ship.xy == Point(0, 0):
                ship.vector.pos = Point(0, 0).move(center).move(offset)


def ships_to_lines(ships) -> list[str]:
    lines = list()
    faction_groups = group_by_faction(ships)
    for members in faction_groups.values():
        for m in members:
            lines.append(str(m))
    return lines


class GameSetup(object):
    def __init__(self, game_directory: GameDirectory, ship_file: ShipFile=None):
        self._dir: GameDirectory = game_directory
        self.shipfile = ship_file if ship_file else ShipFile(self._dir)
        self.ships: dict = self._init_ships(self.shipfile.ship_lines)

    def execute(self):
        self._dir.setup_directories()
        self._dir.clean()
        self.run_tick_zero()
        for faction, ships in group_by_faction(self.ships.values()).items():
            logger.info(f"=={faction}==")
            for ship in ships:
                logger.info(f"Ship: {ship.name}, Faction: {ship.faction}, Pos: {ship.pos}, Type: {ship.class_name}")
        self.save()
        self.report()

    def run_tick_zero(self, distance_from_center=500):
        distribute_factions(self.ships.values(), distance_from_center)
        for ship in self.ships.values():
            ship.history.set_tick(TICK_ZERO)
            ship.scan(self.ships)
            ship.history.update()

    def report(self):
        report_round_zero(self._dir, self.ships.values())

    def _init_ships(self, ship_file: list) -> dict:
        """Load and initialize all the ships to their status at the start of a round."""
        objects_in_space = dict()
        for line in ship_file:
            # position = (int(line.x), int(line.y))
            position = line.xy
            # Always for tick 0 in this case.
            ois = builder.create(line.name, line.type, position)
            ois.player = line.player
            ois.faction = line.faction
            objects_in_space[ois.name] = ois
        return objects_in_space

    def save(self):
        """Save the round 0 pickle file and the ships file with coordinates (to ensure idempotency)."""
        self._dir.save(self.ships, 0)
        self.shipfile.save(self.ships.values())


def setup_game(gd: GameDirectory, ship_file: ShipFile=None) -> Game:
    setup = GameSetup(gd, ship_file)
    logger.info(f"Setup {gd.path} for ship file: {setup.shipfile}")
    setup.execute()
    logger.info(f"Current status: {gd.load_current_status()}")
    return Game(gd)
