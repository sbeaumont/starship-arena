"""
This package holds the base of the component system.

The Component class introduces:
- referencing owner and container
- default hooks that the engine calls that can be overridden
- a parameter system to allow pre-checking of a player's command file.
- a status method to report on the active state of the component, used by the history system and the reporting.

The ComponentParameter classes allow a component to introduce validation of its inputs without leaking
the internals of the component to other parts of the engine.
"""

import re
from abc import ABC

from arena.engine.objects.event import InternalEvent
from arena.engine.parameter import Parameter


class Component(ABC):
    """An object that is attached to an owner (Ship) and can damage other objects in space."""
    def __init__(self, name: str, container=None):
        assert name, "name may not be None"
        self.name = name
        self.container = container

    @property
    def status(self) -> dict:
        """Returns a dictionary of names and values"""
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

    def tick(self, tick_nr):
        pass

    def post_move(self, objects_in_space: dict):
        pass

    def use_energy(self):
        pass

    def activation(self, on_off: bool):
        self.owner.add_event(InternalEvent(f"Component {self.name} can not be activated/deactivated."))

    @property
    def expected_parameters(self):
        return None


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
    """Identifies a named object in space. Example is a laser that fires at a named object instead of a direction."""

    @property
    def needs_ois(self) -> bool:
        return True

    @property
    def is_valid(self):
        assert self._input is not None
        assert self.ois is not None
        self.feedback.clear()
        object_exists = self._input in self.ois
        if not object_exists:
            self.feedback.append(f"{self._input} does not exist.")
        return object_exists

    @property
    def value(self):
        return self.ois.get(self._input, None)


class DirectionParameter(ComponentParameter):
    """Represents a relative direction to the container of a component, like the direction in a Fire command."""
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
    """Represents a binary on/off state. Example is the activation state of a cloak."""

    valid_inputs = ['yes', 'no', 'true', 'false', 'on', 'off', '1', '0']
    on_inputs = ['yes', 'true', 'on', '1']

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


