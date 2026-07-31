"""Puts a replacement in space for a ship that was lost."""

import logging
import re

import arena.engine.objects.registry.builder as builder
from arena.engine.history import Tick
from arena.engine.objects.component import DirectionParameter, ObjectByNameParameter, Whereabouts
from arena.engine.objects.components.weapon import Weapon
from arena.engine.objects.objectinspace import Vector
from arena.engine.world import World

logger = logging.getLogger(__name__)


class ShipSpawner(Weapon):
    """Rebuilds a wreck: same type, same player, same faction, a new hull with no score.

    Nothing about the replacement is chosen by whoever fires it, which is what stops this being
    a way to conjure an arbitrary fleet."""

    # How far off the base a replacement appears, along the direction it was given.
    launch_distance = 10

    def __init__(self, name: str, initial_load: int, firing_arc=None):
        super().__init__(name, firing_arc)
        self.initial_load = initial_load
        self.ammo = initial_load

    @property
    def expected_parameters(self):
        return [ObjectByNameParameter('wreck', self, frozenset({Whereabouts.Graveyard})),
                DirectionParameter('direction', self)]

    def fire(self, params: dict, world: World, tick: Tick):
        wreck = params['wreck'].value
        direction = params['direction'].value

        if not wreck:
            self.add_internal_event(
                f"{self.name}: {params['wreck'].object_name} is not a wreck in this game.")
            return None
        if self.ammo <= 0:
            self.add_internal_event(f"{self.name} has no replacements left.")
            return None
        if self.firing_arc and not self.in_firing_arc(direction):
            self.add_internal_event(f"{self.name} can not spawn at angle {direction}: {self.firing_arc}.")
            return None

        self.ammo -= 1
        heading = (self.container.heading + direction) % 360
        vector = Vector(pos=self.container.xy.translate(heading, self.launch_distance),
                        heading=heading, speed=0)
        replacement = builder.spawn(wreck.type_name, self.replacement_name(wreck.name, world),
                                    vector, tick=tick, player=wreck.player)
        replacement.faction = wreck.faction
        self.add_internal_event(
            f"{self.name} replaced {wreck.name} with {replacement.name} for {wreck.player}.")
        return replacement

    @staticmethod
    def replacement_name(wreck_name: str, world: World) -> str:
        """Voyager becomes Voyager-2, and Voyager-3 once that one has gone too.

        A name is never handed out twice, because command files are named after their ship."""
        stem = re.sub(r'-\d+$', '', wreck_name)
        used = world.all_names
        number = 2
        while f"{stem}-{number}" in used:
            number += 1
        return f"{stem}-{number}"

    @property
    def status(self):
        return {'Replacements': self.ammo}

    @property
    def description(self):
        return f"Ship spawner ({self.initial_load})"