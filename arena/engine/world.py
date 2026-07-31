"""What an object can ask about the game beyond itself.

Passed down every engine hook in place of a bare dict of objects, so a component that needs to
know something world-spanning has somewhere to ask. Saved whole, once per round, which is what
keeps a round's wrecks the ones that had died by then."""


class World(object):
    def __init__(self, objects: dict = None, graveyard: dict = None):
        self.objects = objects if objects is not None else dict()
        self.graveyard = graveyard if graveyard is not None else dict()

    def add(self, ois):
        self.objects[ois.name] = ois

    def remove(self, ois):
        del self.objects[ois.name]

    def add_to_graveyard(self, ois):
        self.graveyard[ois.name] = ois

    def move_to_graveyard(self, ois):
        self.remove(ois)
        self.add_to_graveyard(ois)

    def known_to(self, ship) -> dict:
        """Every name this ship may legitimately use in an order.

        Wider than what still exists: validating against existence alone would reject an order
        aimed at something that has since been destroyed, and thereby tell the player it is gone.
        The order is accepted and simply fails when it is fired."""
        known = dict(self.objects)
        known.update(self.graveyard)
        for tick_history in ship.history.ticks.values():
            for scan in tick_history.scans:
                known.setdefault(scan.name, scan.source)
        return known