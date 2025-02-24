from abc import ABC

from arena.engine import Component


class Weapon(Component, ABC):
    """An object that is attached to an owner (Ship) and can damage other objects in space."""
    def __init__(self, name: str, firing_arc: tuple = None):
        super().__init__(name)
        if firing_arc:
            assert len(firing_arc) == 2
            assert 0 <= firing_arc[0] <= 360
            assert 0 <= firing_arc[1] <= 360
        self.firing_arc = firing_arc

    def fire(self, params: dict, objects_in_space: dict):
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
        return {
            'Firing Arc': self.firing_arc if self.firing_arc else '360'
        }


