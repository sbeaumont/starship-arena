from abc import ABC

from arena.engine.history import Tick
from arena.engine.world import World
from arena.engine.objects.component import Component


class Weapon(Component, ABC):
    """A component a Fire order triggers. Most of them damage something; a Gravscan sweeps."""

    # Weapons that consume ammunition shadow this with a count of what is left. Ammo is
    # spent for the rest of the game unless the ship replenishes.
    ammo = None

    # Weapons that put something into space shadow this with the type they launch.
    payload_type = None

    def __init__(self, name: str, firing_arc: tuple = None):
        super().__init__(name)
        if firing_arc:
            assert len(firing_arc) == 2
            assert 0 <= firing_arc[0] <= 360
            assert 0 <= firing_arc[1] <= 360
        self.firing_arc = firing_arc

    def fire(self, params: dict, world: World, tick: Tick):
        raise NotImplementedError

    def in_firing_arc(self, angle):
        """Determine if an angle is in the firing arc of the weapon."""
        if not self.firing_arc:
            # If no arc is given, 360 degree arc is assumed.
            return True

        angle = angle % 360
        left, right = self.firing_arc
        if left > right:
            # Arc passes through 0, e.g. 270 -> 0 -> 90
            return (left <= angle) or (angle <= right)
        else:
            # Arc does not pass through 0, e.g. 90 -> 225
            return left <= angle <= right

    @property
    def status(self) -> dict:
        return dict()


