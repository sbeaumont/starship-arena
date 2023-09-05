from collections import defaultdict
from dataclasses import dataclass
from math import cos, sin, radians
from random import randint

from engine.gamedirectory import GameDirectory
from ois.objectinspace import Point
from rep.visualize import Visualizer
import ois.registry.builder as builder
from rep.report import report_round_zero
from rep.history import TICK_ZERO, Tick


@dataclass
class Ship:
    name: str
    type: str
    faction: str
    player: str = ''
    x: float = 0
    y: float = 0

    def move(self, xy: tuple):
        self.x += xy[0]
        self.y += xy[1]
        return self

    def __str__(self):
        return f"{self.name},{self.type},{self.faction},{self.player},{round(self.x)},{round(self.y)}"


def load_ship_file(file_name) -> list:
    with open(file_name) as f:
        lines = [line.strip().split() for line in f.readlines()]
    field_defs = {sl[1]: sl[0] for sl in enumerate(lines[0])}
    ships = list()
    for line in lines[1:]:
        ship = Ship(
            name=line[field_defs['Name']],
            type=line[field_defs['Type']],
            faction=line[field_defs['Faction']],
            player=line[field_defs['Player']]
        )
        ships.append(ship)
    return ships


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


def distribute_factions(ships, distance):
    factions = {s.faction for s in ships}
    faction_centers = centers_for(len(factions), distance, angle_tweak=(-10, 10), distance_tweak=(-30, 60))
    faction_groups = group_by_faction(ships)
    for center, group in zip(faction_centers, faction_groups.values()):
        num_ships_in_faction = len(group)
        offsets = centers_for(num_ships_in_faction, 20, angle_tweak=(-30, 30), distance_tweak=(0, 30))
        for ship, offset in zip(group, offsets):
            ship.vector.pos = Point(0, 0).move(center).move(offset)


def ships_to_lines(ships) -> list[str]:
    lines = list()
    faction_groups = group_by_faction(ships)
    for members in faction_groups.values():
        for m in members:
            lines.append(str(m))
    return lines


class GameSetup(object):
    def __init__(self, game_directory: GameDirectory):
        self._dir: GameDirectory = game_directory
        self.ships: dict = self._init_ships()

    def run(self, distance_from_center=500):
        distribute_factions(self.ships.values(), distance_from_center)
        for ship in self.ships.values():
            ship.history.set_tick(TICK_ZERO)
            ship.scan(self.ships)
            ship.history.update()

    def report(self):
        report_round_zero(self._dir.path, self.ships.values())

    def _init_ships(self) -> dict:
        """Load and initialize all the ships to their status at the start of a round."""
        objects_in_space = dict()
        for line in load_ship_file(self._dir.init_file):
            # position = (int(line.x), int(line.y))
            position = (0, 0)
            # Always for tick 0 in this case.
            ois = builder.create(line.name, line.type, position)
            ois.player = line.player
            ois.faction = line.faction
            objects_in_space[ois.name] = ois
        return objects_in_space

    def save(self):
        self._dir.save(self.ships, 0)

