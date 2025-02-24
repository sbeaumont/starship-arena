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
    def is_valid(self):
        ...

    def input(self, input):
        self._input = input

    @property
    def value(self):
        return self._input
