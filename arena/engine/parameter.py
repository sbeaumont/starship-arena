"""
Abstract base class for all Parameter objects. In a separate file to prevent circular dependencies.
"""

from abc import ABC, abstractmethod


class Parameter(ABC):
    def __init__(self, name):
        self.name = name
        self._input = None
        self.ois = None
        self.feedback = list()

    @property
    def number_of_inputs(self) -> int:
        return 1

    def append_feedback(self, feedback_list):
        feedback_list.extend(self.feedback)

    @property
    def needs_ois(self) -> bool:
        return False

    def set_ois(self, ois):
        self.ois = ois

    @property
    @abstractmethod
    def kind(self) -> str:
        """What sort of input this takes, e.g. 'direction' or 'object_name'.

        Interfaces use this to offer the right control - an angle to drag, a target to
        click, a slider - instead of asking the player to type. It says nothing about
        whether a given input is acceptable: is_valid remains the authority on that.
        """
        ...

    @property
    @abstractmethod
    def is_valid(self):
        ...

    def input(self, input):
        self._input = input

    @property
    def value(self):
        return self._input
