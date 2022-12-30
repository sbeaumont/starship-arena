from collections import defaultdict
from dataclasses import dataclass
from math import cos, sin, radians
from random import randint

from ois.objectinspace import Point
from rep.visualize import Visualizer


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


def load_ship_file(file_name):
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


def polar_to_cartesian(r, theta):
    """theta in degrees

    returns tuple; (float, float); (x, y)
    """
    x = r * cos(radians(theta))
    y = r * sin(radians(theta))
    return round(x), round(y)


def centers_for(num_factions, distance, random_rotation=60, angle_tweak=(0, 0), distance_tweak=(0, 0)):
    result = list()
    rotation = randint(0, random_rotation)
    for i in range(num_factions):
        angle = (i * int(360 / num_factions)) + rotation
        tweaked_angle = angle + randint(*angle_tweak)
        tweaked_distance = distance + randint(*distance_tweak)
        result.append(polar_to_cartesian(tweaked_distance, tweaked_angle))
    return result


def group_by_faction(ships):
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
            ship.move(center).move(offset)


def ships_to_lines(ships):
    lines = list()
    faction_groups = group_by_faction(ships)
    for members in faction_groups.values():
        for m in members:
            lines.append(str(m))
    return lines


if __name__ == '__main__':
    distance_from_origin = 500
    all_ships = load_ship_file('test-games/test-game-3/ships.txt')
    distribute_factions(all_ships, distance_from_origin)

    # all_positions = [(s.x, s.y) for s in all_ships]
    # visualise_points(all_positions)

    for line in ships_to_lines(all_ships):
        print(line)
