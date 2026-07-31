"""What an object can ask about the game beyond itself.

Passed down every engine hook in place of a bare dict of objects, so a component that needs to
know something world-spanning has somewhere to ask. Saved whole, once per round, which is what
keeps a round's wrecks the ones that had died by then."""


class World(object):
    def __init__(self, gd, objects: dict = None, graveyard: dict = None, spawns: dict = None):
        self._dir = gd
        self.objects = objects if objects is not None else dict()
        self.graveyard = graveyard if graveyard is not None else dict()
        self.spawns = spawns if spawns is not None else dict()

    def __getstate__(self):
        """The directory is where this world is kept, not part of what it is."""
        state = self.__dict__.copy()
        del state['_dir']
        return state

    def kept_in(self, gd):
        """Hand back the directory a loaded world was read from."""
        self._dir = gd

    def save(self, round_nr: int):
        self._dir.save_world(self, round_nr)

    def add(self, ois):
        self.objects[ois.name] = ois

    def remove(self, ois):
        del self.objects[ois.name]

    def add_to_graveyard(self, ois):
        self.graveyard[ois.name] = ois

    def move_to_graveyard(self, ois):
        self.remove(ois)
        self.add_to_graveyard(ois)

    def plan_spawn(self, ois):
        """Something due to arrive rather than to have started the game.

        Planning the same one twice plans it once, so a round that is set up more than once
        does not double anything."""
        self.spawns[ois.name] = ois

    def spawn(self, tick):
        """Put everything planned for this tick into space.

        A planned object opens its history at the tick it is due, so it says for itself when its
        moment is. They stay listed once they have arrived: that they did is a fact about the
        world, and the tick has passed so none of them can arrive twice."""
        for ois in [o for o in self.spawns.values() if o.history.first == tick]:
            self.add(ois)

    @property
    def all_objects(self) -> dict:
        """Everything this world holds, by name: in space, in the graveyard, due to arrive.

        One that has arrived is in two of them, and is the same object either way."""
        return {**self.spawns, **self.graveyard, **self.objects}

    @property
    def player_objects(self) -> dict:
        """Everything with somebody at the helm, wherever it is: in space, dead, or due.

        What a caller wants off them is the caller's business."""
        return {name: o for name, o in self.all_objects.items() if o.is_player_controlled}

    @property
    def all_names(self) -> set:
        """Every name the game has used, so none is handed out twice.

        Command files are named after their ship, so a reused name would inherit a dead one's
        orders."""
        return set(self.all_objects)

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