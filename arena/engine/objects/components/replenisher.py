"""Restocks a ship that has come alongside. The base's side of a replenish."""

import logging

from arena.engine.history import Tick
from arena.engine.objects.component import ObjectByNameParameter
from arena.engine.objects.components.weapon import Weapon
from arena.engine.objects.event import ReplenishEvent
from arena.engine.world import Whereabouts, World

logger = logging.getLogger(__name__)


class ShipToRestockParameter(ObjectByNameParameter):
    """Every ship in the game, whether or not it is alongside yet.

    An order is written ten ticks before it runs, so what is in reach while planning says nothing
    about what will be in reach when it fires. Ordnance and terrain carry no faction of their own,
    which is what leaves them out."""

    def __init__(self, name: str, component):
        super().__init__(name, component, where=frozenset({Whereabouts.Objects}))

    @property
    def choices(self) -> list:
        return sorted(name for name, ois in self.world.find_objects(where=self.where).items()
                      if ois.faction and ois is not self.component.container)


class Replenisher(Weapon):
    """Fills a ship up again: hull, battery, shields, heat and every magazine.

    Whose ship it is, is not asked. See GDDR 0032."""

    # How far it reaches, and how slowly a ship has to be going to be caught by it.
    range = 10
    max_approach_speed = 10

    @property
    def expected_parameters(self):
        return [ShipToRestockParameter('ship', self)]

    def fire(self, params: dict, world: World, tick: Tick):
        ship = params['ship'].value
        if not ship:
            self.add_internal_event(f"{self.name}: {params['ship'].object_name} is not in space.")
            return None
        if ship is self.container:
            self.add_internal_event(f"{self.name} can not restock the base it is mounted on.")
            return None
        if not ship.faction:
            self.add_internal_event(f"{self.name}: {ship.name} is not a ship it can restock.")
            return None
        distance = self.container.distance_to(ship.xy)
        if distance > self.range:
            self.add_internal_event(
                f"{self.name}: {ship.name} is {distance} away, beyond the {self.range} it reaches.")
            return None
        if ship.speed > self.max_approach_speed:
            self.add_internal_event(
                f"{self.name}: {ship.name} is passing at {ship.speed}, too fast to hold.")
            return None

        ship.replenish()
        self.owner.add_event(ReplenishEvent(f"Replenished {ship.name}"))
        ship.add_event(ReplenishEvent(f"Replenished by {self.container.name}"))
        return None

    @property
    def description(self):
        return f"Replenisher (to {self.range}, up to speed {self.max_approach_speed})"