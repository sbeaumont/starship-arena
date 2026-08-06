"""The component system: the parts a machine is built from.

A component answers for itself what orders it takes, what its state is and what its type says it
is. See docs/adr/0004-components-own-their-parameters.md.

The methods below are the whole vocabulary a machine has for talking to its parts. It asks all of
them the same questions and names none of them, so a new component needs no machine changed: see
docs/adr/0019-machines-drive-components-through-one-vocabulary.md."""

import re
from abc import ABC

from arena.engine.history import Tick
from arena.engine.world import Whereabouts, World
from arena.engine.objects.event import InternalEvent
from arena.engine.parameter import Parameter


class Component(ABC):
    """An object that is attached to an owner (Ship) and can do stuff."""

    # How far this component acts into space. Components that reach shadow this, the way a
    # Warhead does with its blast radius; a cloak or a pilot really does reach nowhere.
    range = 0

    def __init__(self, name: str, container=None):
        assert name, "name may not be None"
        self.name = name
        self.container = container

    @property
    def status(self) -> dict:
        """Names and values of what changes about this component during play."""
        raise NotImplementedError

    @property
    def owner(self):
        return self.container.owner

    @property
    def description(self):
        return self.__class__.__name__

    def add_internal_event(self, message: str):
        self.owner.add_event(InternalEvent(message))

    def attach(self, container):
        self.container = container

    def reset(self):
        pass

    def round_reset(self):
        pass

    def post_round_reset(self):
        pass

    def tick(self, tick: Tick):
        pass

    def encounter(self, world: World):
        """Nothing a component reaches ends its machine's leg, unless it says otherwise."""
        return None

    def post_move(self, world: World):
        pass

    def decide(self, world: World, tick: Tick):
        pass

    def use_energy(self):
        pass

    def activation(self, on_off: bool):
        self.owner.add_event(InternalEvent(f"Component {self.name} can not be activated/deactivated."))

    def power_up(self, amount: int):
        self.owner.add_event(InternalEvent(f"Component {self.name} can not be powered."))

    @property
    def expected_parameters(self):
        return []


class ComponentParameter(Parameter):
    def __init__(self, name: str, component: Component):
        super().__init__(name)
        self.component = component


class ComponentSelectorParameter(Parameter):
    """Represents a specific named component, for instance which weapon in a Fire command."""

    def __init__(self, name: str, owner, component_name: str):
        super().__init__(name)
        self.owner = owner
        self.input(component_name)

    @property
    def kind(self) -> str:
        return 'component'

    @property
    def is_valid(self):
        assert self._input is not None
        self.feedback.clear()
        comp_exists = False
        if isinstance(self._input, str) and self._input.isalnum():
            comp_exists = self._input in self.owner.all_components
            if not comp_exists:
                self.feedback.append(f"Component '{self._input}' not found.")
        return comp_exists

    @property
    def value(self):
        return self.owner.all_components[self._input]


class ObjectByNameParameter(ComponentParameter):
    """Identifies a named object. A laser names what it shoots at, a spawner names a wreck."""

    def __init__(self, name: str, component: Component,
                 where=frozenset({Whereabouts.Objects}),
                 with_tags=frozenset(), without_tags=frozenset(), own_faction=False):
        super().__init__(name, component)
        self.where = where
        self.with_tags = with_tags
        self.without_tags = without_tags
        self.own_faction = own_faction

    @property
    def kind(self) -> str:
        return 'object_name'

    @property
    def needs_world(self) -> bool:
        return True

    @property
    def is_valid(self):
        assert self._input is not None
        assert self.world is not None
        self.feedback.clear()
        # Every name the ship could know, not only what is still in space, so an order aimed
        # at something already destroyed is accepted rather than giving that away.
        is_known = self._input in self.world.known_to(self.component.container)
        if not is_known:
            self.feedback.append(f"{self._input} is not a known object name.")
        return is_known

    @property
    def choices(self) -> list | None:
        """What to offer, or None for something picked off the map instead."""
        if self.where == frozenset({Whereabouts.Objects}):
            return None
        return sorted(self.world.find_objects(
            where=self.where, with_tags=self.with_tags, without_tags=self.without_tags,
            faction=self.component.container.faction if self.own_faction else None))

    @property
    def value(self):
        """A laser looks in space only, so a shot at something since destroyed fizzles rather
        than hitting a corpse."""
        return self.world.find_objects(where=self.where).get(self._input)

    @property
    def object_name(self):
        return self._input


class DirectionParameter(ComponentParameter):
    """Represents a relative direction to the container of a component, like the direction in a Fire command."""
    @property
    def kind(self) -> str:
        return 'direction'

    @property
    def is_valid(self):
        assert self._input is not None
        assert hasattr(self.component, 'in_firing_arc')
        self.feedback.clear()
        if re.match(r"-?[0-9]+", self._input):
            result = self.component.in_firing_arc(int(self._input))
            if not result:
                self.feedback.append(f"{self._input} is not a valid firing angle.")
        else:
            self.feedback.append(f"{self.name}: {self._input} is not a valid number.")
            result = False
        return result

    @property
    def value(self):
        return int(self._input)


class NumberInRangeParameter(ComponentParameter):
    """Represents a number that must be in a specified range."""
    def __init__(self, name: str, component: Component, range: tuple):
        super().__init__(name, component)
        self.range = range

    @property
    def kind(self) -> str:
        return 'number_in_range'

    @property
    def is_valid(self):
        assert self._input is not None
        self.feedback.clear()
        if re.match(r"-?[0-9]+", self._input):
            result = self.range[0] <= int(self._input) <= self.range[1]
            if not result:
                self.feedback.append(f"{self.name}: {self._input} not in range [{self.range[0]}, {self.range[1]}].")
        else:
            self.feedback.append(f"{self.name}: {self._input} is not a valid number")
            result = False
        return result

    @property
    def value(self):
        return int(self._input)


class OnOffParameter(ComponentParameter):
    """Represents a binary on/off state, for a component that is switched rather than set."""

    valid_inputs = ['yes', 'no', 'true', 'false', 'on', 'off', '1', '0']
    on_inputs = ['yes', 'true', 'on', '1']

    @property
    def kind(self) -> str:
        return 'on_off'

    @property
    def is_valid(self):
        assert self._input is not None
        assert isinstance(self._input, str)
        self.feedback.clear()
        if self._input.lower() in self.valid_inputs:
            result = True
        else:
            self.feedback.append(f"{self._input} is not a valid input ({', '.join(self.valid_inputs)})")
            result = False
        return result

    @property
    def value(self):
        return self._input in self.on_inputs


