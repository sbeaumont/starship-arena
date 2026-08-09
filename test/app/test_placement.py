"""Deploying a roster: where a scenario puts its factions, and which way they look."""

import random
import unittest
from math import cos, hypot, radians, sin

from arena.app.scenarios.placement import SPREAD, distribute_factions

DISTANCE = 500

ROSTER = [
    {'name': 'One-1', 'type': 'H2545', 'faction': 'One'},
    {'name': 'One-2', 'type': 'H2552', 'faction': 'One'},
    {'name': 'Two-1', 'type': 'F2547', 'faction': 'Two'},
    {'name': 'Three-1', 'type': 'A2527', 'faction': 'Three'},
]


def _deploy(ships=None, **kwargs) -> dict:
    placed = distribute_factions(ships or ROSTER, random.Random(7), DISTANCE, **kwargs)
    return {ship['name']: ship for ship in placed}


def _closing(ship: dict) -> float:
    """How much of a step along its heading takes a ship towards (0, 0). Straight at it is 1."""
    angle = radians(ship['heading'])
    return -(sin(angle) * ship['x'] + cos(angle) * ship['y']) / hypot(ship['x'], ship['y'])


class TestDeployingARoster(unittest.TestCase):
    def test_every_ship_is_placed(self):
        for ship in _deploy().values():
            self.assertNotEqual((0, 0), (ship['x'], ship['y']), f"{ship['name']} was never placed")

    def test_the_roster_comes_back_in_the_order_it_went_in(self):
        placed = distribute_factions(ROSTER, random.Random(7), DISTANCE)
        self.assertEqual([s['name'] for s in ROSTER], [s['name'] for s in placed])

    def test_everybody_starts_the_same_distance_out(self):
        for ship in _deploy().values():
            self.assertAlmostEqual(DISTANCE, hypot(ship['x'], ship['y']), delta=SPREAD + 1)

    def test_a_faction_lands_together_and_the_others_do_not(self):
        deployed = _deploy()
        together = hypot(deployed['One-1']['x'] - deployed['One-2']['x'],
                         deployed['One-1']['y'] - deployed['One-2']['y'])
        apart = hypot(deployed['One-1']['x'] - deployed['Two-1']['x'],
                      deployed['One-1']['y'] - deployed['Two-1']['y'])
        self.assertLess(together, apart)

    def test_everyone_looks_at_the_middle(self):
        for ship in _deploy().values():
            self.assertAlmostEqual(1, _closing(ship), places=3)

    def test_a_scenario_can_ask_for_no_facing_at_all(self):
        for ship in _deploy(face_middle=False).values():
            self.assertNotIn('heading', ship)

    def test_coordinates_the_roster_gave_are_kept_and_still_face_the_middle(self):
        placed = _deploy([dict(ROSTER[0], x=17, y=-99)] + ROSTER[1:])

        self.assertEqual((17, -99), (placed['One-1']['x'], placed['One-1']['y']))
        self.assertAlmostEqual(1, _closing(placed['One-1']), places=3)