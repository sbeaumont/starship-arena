"""
Administrative features
- setting up a new game.
"""

from collections import defaultdict
from dataclasses import dataclass
from math import cos, sin, radians
from random import randint
import logging

from engine.gamedirectory import GameDirectory
from ois.objectinspace import Point
from rep.visualize import Visualizer
import ois.registry.builder as builder
from rep.report import report_round_zero
from rep.history import TICK_ZERO

logger = logging.getLogger('starship-arena.admin')


class ShipFile(object):
    @dataclass
    class ShipFileLine:
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

        @property
        def xy(self):
            return self.x, self.y

        def __str__(self):
            return f"{self.name},{self.type},{self.faction},{self.player},{round(self.x)},{round(self.y)}"

    def __init__(self, gd: GameDirectory, premade_lines: str = None):
        self.gd = gd
        text_lines = [line.strip().split() for line in premade_lines.splitlines()] if premade_lines else self.load()
        self.ship_lines = self.ship_lines_to_objects(text_lines)

    def load(self) -> list:
        with open(self.gd.init_file) as f:
            return [line.strip().split() for line in f.readlines()]

    def save(self, ships: list):
        with open(self.gd.init_file, 'w') as f:
            file_contents = '\n'.join(self.ship_file_with_coordinates(ships))
            f.write(file_contents)

    def ship_lines_to_objects(self, lines: list):
        field_defs = {sl[1]: sl[0] for sl in enumerate(lines[0])}
        ships = list()
        for line in lines[1:]:
            try:
                if line[0].strip().startswith('#'):
                    # Ignore lines that start with #
                    continue
                ship = ShipFile.ShipFileLine(
                    name=line[field_defs['Name']],
                    type=line[field_defs['Type']],
                    faction=line[field_defs['Faction']],
                    player=line[field_defs['Player']]
                )
                if 'X' in field_defs and 'Y' in field_defs:
                    x = int(line[field_defs['X']])
                    y = int(line[field_defs['Y']])
                    ship.move((x, y))
                ships.append(ship)
            except (KeyError, ValueError):
                logger.error(f"Failed to process <{line}>")
                print(line)
                raise
        return ships

    def ship_file_with_coordinates(self, ships: list):
        fields = ['name', 'type', 'faction', 'player', 'x', 'y']
        max_lengths = {
            'name': max(max([len(s.name) for s in ships]), len('name')),
            'type': max(max([len(s._type.__class__.__name__) for s in ships]), len('type')),
            'faction': max(max([len(s.faction) for s in ships]), len('faction')),
            'player': max(max([len(s.player) for s in ships]), len('player')),
            'x': max(max([len(str(s.pos.x)) for s in ships]), len('x')),
            'y': max(max([len(str(s.pos.y)) for s in ships]), len('y'))
        }

        lines = list()
        header_line = ' '.join([fieldname.capitalize().rjust(max_lengths[fieldname]) for fieldname in fields])
        lines.append(header_line)
        for ship in ships:
            line_values = {
                'name': ship.name,
                'type': ship._type.__class__.__name__,
                'faction': ship.faction,
                'player': ship.player,
                'x': ship.pos.x,
                'y': ship.pos.y
            }
            ship_line = ' '.join([str(line_values[fieldname]).rjust(max_lengths[fieldname]) for fieldname in fields])
            lines.append(ship_line)
        return lines


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
    def __init__(self, game_directory: GameDirectory, shipfile: ShipFile = None):
        self._dir: GameDirectory = game_directory
        self.shipfile = shipfile if shipfile else ShipFile(self._dir)
        self.ships: dict = self._init_ships(self.shipfile.ship_lines)

    def execute(self):
        self.run()
        self.save()
        self.report()

    def run(self, distance_from_center=500):
        distribute_factions(self.ships.values(), distance_from_center)
        for ship in self.ships.values():
            ship.history.set_tick(TICK_ZERO)
            ship.scan(self.ships)
            ship.history.update()

    def report(self):
        report_round_zero(self._dir.path, self.ships.values())

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


def setup_game(gd: GameDirectory, shipfile: ShipFile = None) -> None:
    logger.info(f"Setup {gd.path}")
    gd.setup_directories()
    gd.clean()
    setup = GameSetup(gd, shipfile)
    setup.run()

    for faction, ships in group_by_faction(setup.ships.values()).items():
        logger.info(f"=={faction}==")
        for ship in ships:
            logger.info(f"Ship: {ship.name}, Faction: {ship.faction}, Pos: {ship.pos}, Type: {ship.type_name}")
    setup.save()
    setup.report()
    logger.info(f"Current status: {gd.load_current_status()}")
